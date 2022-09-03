# -*- coding: utf-8 -*-
#
# This file is part of INGInious. See the LICENSE and the COPYRIGHTS files for
# more information about the licensing of this file.

""" Pages that allow editing of tasks """
import json
import logging
import tempfile
import bson

import flask
from collections import OrderedDict
from zipfile import ZipFile
from flask import redirect
from werkzeug.exceptions import NotFound

from inginious.frontend.tasks import _migrate_from_v_0_6
from inginious.frontend.accessible_time import AccessibleTime
from inginious.frontend.pages.course_admin.utils import INGIniousAdminPage

from inginious.common.base import dict_from_prefix, id_checker
from inginious.common.exceptions import TaskNotFoundException
from inginious.frontend.pages.course_admin.task_edit_file import CourseTaskFiles
from inginious.frontend.tasks import Task


class CourseEditTask(INGIniousAdminPage):
    """ Edit a task """
    _logger = logging.getLogger("inginious.webapp.task_edit")

    def GET_AUTH(self, courseid, taskid):  # pylint: disable=arguments-differ
        """ Edit a task """
        if not id_checker(taskid):
            raise NotFound(description=_("Invalid task id"))

        course, __ = self.get_course_and_check_rights(courseid, allow_all_staff=False)

        try:
            task_data = self.task_factory.get_task_descriptor_content(courseid, taskid)
        except TaskNotFoundException:
            raise NotFound()

        # Ensure retrocompatibility
        task_data = _migrate_from_v_0_6(task_data)

        environment_types = self.environment_types
        environments = self.environments

        current_filetype = None
        try:
            current_filetype = self.task_factory.get_task_descriptor_extension(courseid, taskid)
        except:
            pass
        available_filetypes = self.task_factory.get_available_task_file_extensions()

        additional_tabs = self.plugin_manager.call_hook('task_editor_tab', course=course, taskid=taskid,
                                                        task_data=task_data, template_helper=self.template_helper)

        return self.template_helper.render("course_admin/task_edit.html", course=course, taskid=taskid,
                                           problem_types=self.task_factory.get_problem_types(), task_data=task_data,
                                           environment_types=environment_types, environments=environments,
                                           problemdata=json.dumps(task_data.get('problems', {})),
                                           contains_is_html=self.contains_is_html(task_data),
                                           current_filetype=current_filetype,
                                           available_filetypes=available_filetypes, AccessibleTime=AccessibleTime,
                                           file_list=CourseTaskFiles.get_task_filelist(self.task_factory, courseid, taskid),
                                           additional_tabs=additional_tabs)

    @classmethod
    def contains_is_html(cls, data):
        """ Detect if the problem has at least one "xyzIsHTML" key """
        for key, val in data.items():
            if isinstance(key, str) and key.endswith("IsHTML"):
                return True
            if isinstance(val, (OrderedDict, dict)) and cls.contains_is_html(val):
                return True
        return False

    def parse_problem(self, problem_content):
        """ Parses a problem, modifying some data """
        del problem_content["@order"]
        return self.task_factory.get_problem_types().get(problem_content["type"]).parse_problem(problem_content)

    def wipe_task(self, courseid, taskid):
        """ Wipe the data associated to the taskid from DB"""
        submissions = self.database.submissions.find({"courseid": courseid, "taskid": taskid})
        for submission in submissions:
            for key in ["input", "archive"]:
                if key in submission and type(submission[key]) == bson.objectid.ObjectId:
                    self.submission_manager.get_gridfs().delete(submission[key])

        self.database.user_tasks.delete_many({"courseid": courseid, "taskid": taskid})
        self.database.submissions.delete_many({"courseid": courseid, "taskid": taskid})

        self._logger.info("Task %s/%s wiped.", courseid, taskid)

    def POST_AUTH(self, courseid, taskid):  # pylint: disable=arguments-differ
        """ Edit a task """
        if not id_checker(taskid) or not id_checker(courseid):
            raise NotFound(description=_("Invalid course/task id"))

        course, __ = self.get_course_and_check_rights(courseid, allow_all_staff=False)
        data = flask.request.form.copy()
        data["task_file"] = flask.request.files.get("task_file")

        # Delete task ?
        if "delete" in data:
            toc = course.get_task_dispenser().get_dispenser_data()
            toc.remove_task(taskid)
            self.course_factory.update_course_descriptor_element(courseid, 'toc', toc.to_structure())
            self.task_factory.delete_task(courseid, taskid)
            if data.get("wipe", False):
                self.wipe_task(courseid, taskid)
            return  redirect(self.app.get_homepath() + "/admin/"+courseid+"/tasks")

        # Else, parse content
        try:
            try:
                task_zip = data.get("task_file").read()
            except:
                task_zip = None
            del data["task_file"]

            problems = dict_from_prefix("problem", data)
            environment_type = data.get("environment_type", "")
            environment_parameters = dict_from_prefix("envparams", data).get(environment_type, {})
            environment_id = dict_from_prefix("environment_id", data).get(environment_type, "")

            data = {key: val for key, val in data.items() if
                    not key.startswith("problem")
                    and not key.startswith("envparams")
                    and not key.startswith("environment_id")
                    and not key.startswith("/")
                    and not key == "@action"}

            data["environment_id"] = environment_id # we do this after having removed all the environment_id[something] entries

            # Determines the task filetype
            if data["@filetype"] not in self.task_factory.get_available_task_file_extensions():
                return json.dumps({"status": "error", "message": _("Invalid file type: {}").format(str(data["@filetype"]))})
            file_ext = data["@filetype"]
            del data["@filetype"]

            # Parse and order the problems (also deletes @order from the result)
            if problems is None:
                data["problems"] = OrderedDict([])
            else:
                data["problems"] = OrderedDict([(key, self.parse_problem(val))
                                                for key, val in sorted(iter(problems.items()), key=lambda x: int(x[1]['@order']))])

            # Task environment parameters
            data["environment_parameters"] = environment_parameters

            # Groups
            if "groups" in data:
                data["groups"] = True if data["groups"] == "true" else False

            # Submission limits
            if "submission_limit" in data:
                if data["submission_limit"] == "none":
                    result = {"amount": -1, "period": -1}
                elif data["submission_limit"] == "hard":
                    try:
                        result = {"amount": int(data["submission_limit_hard"]), "period": -1}
                    except:
                        return json.dumps({"status": "error", "message": _("Invalid submission limit!")})

                else:
                    try:
                        result = {"amount": int(data["submission_limit_soft_0"]), "period": int(data["submission_limit_soft_1"])}
                        if result['period'] < 0:
                            return json.dumps({"status": "error", "message": _("The soft limit period must be positive!")})
                    except:
                        return json.dumps({"status": "error", "message": _("Invalid submission limit!")})

                if data['submission_limit'] != 'none' and result['amount'] < 0:
                    return json.dumps({"status": "error", "message": _("The submission limit must be positive!")})

                del data["submission_limit_hard"]
                del data["submission_limit_soft_0"]
                del data["submission_limit_soft_1"]
                data["submission_limit"] = result

            # Accessible
            if data["accessible"] == "custom":
                data["accessible"] = "{}/{}/{}".format(data["accessible_start"], data["accessible_soft_end"], data["accessible_end"])
            elif data["accessible"] == "true":
                data["accessible"] = True
            else:
                data["accessible"] = False
            del data["accessible_start"]
            del data["accessible_end"]
            del data["accessible_soft_end"]
            try:
                AccessibleTime(data["accessible"])
            except Exception as message:
                return json.dumps({"status": "error", "message": _("Invalid task accessibility ({})").format(message)})

            # Random inputs
            try:
                data['input_random'] = int(data['input_random'])
            except:
                return json.dumps({"status": "error", "message": _("The number of random inputs must be an integer!")})
            if data['input_random'] < 0:
                return json.dumps({"status": "error", "message": _("The number of random inputs must be positive!")})

            # Checkboxes
            if data.get("responseIsHTML"):
                data["responseIsHTML"] = True

            # Network grading
            data["network_grading"] = "network_grading" in data
        except Exception as message:
            return json.dumps({"status": "error", "message": _("Your browser returned an invalid form ({})").format(message)})

        # Get the course
        try:
            course = self.course_factory.get_course(courseid)
        except:
            return json.dumps({"status": "error", "message": _("Error while reading course's informations")})

        # Get original data
        try:
            orig_data = self.task_factory.get_task_descriptor_content(courseid, taskid)
            data["order"] = orig_data["order"]
        except:
            pass

        task_fs = self.task_factory.get_task_fs(courseid, taskid)
        task_fs.ensure_exists()

        # Call plugins and return the first error
        plugin_results = self.plugin_manager.call_hook('task_editor_submit', course=course, taskid=taskid,
                                                       task_data=data, task_fs=task_fs)

        # Retrieve the first non-null element
        error = next(filter(None, plugin_results), None)
        if error is not None:
            return error

        try:
            Task(course, taskid, data, self.course_factory.get_fs(), self.plugin_manager, self.task_factory.get_problem_types())
        except Exception as message:
            return json.dumps({"status": "error", "message": _("Invalid data: {}").format(str(message))})

        if task_zip:
            try:
                zipfile = ZipFile(task_zip)
            except Exception:
                return json.dumps({"status": "error", "message": _("Cannot read zip file. Files were not modified")})

            with tempfile.TemporaryDirectory() as tmpdirname:
                try:
                    zipfile.extractall(tmpdirname)
                except Exception:
                    return json.dumps(
                        {"status": "error", "message": _("There was a problem while extracting the zip archive. Some files may have been modified")})
                task_fs.copy_to(tmpdirname)

        self.task_factory.delete_all_possible_task_files(courseid, taskid)
        self.task_factory.update_task_descriptor_content(courseid, taskid, data, force_extension=file_ext)

        return json.dumps({"status": "ok"})
