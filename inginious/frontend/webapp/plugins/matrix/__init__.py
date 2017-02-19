# -*- coding: utf-8 -*-
#
# This file is part of INGInious. See the LICENSE and the COPYRIGHTS files for
# more information about the licensing of this file.

""" Matrix plugin - show course overview of student grades """
import logging
import web
from inginious.frontend.webapp.pages.course_admin.utils import INGIniousAdminPage
from datetime import datetime


class MatrixPage(INGIniousAdminPage):
    def GET_AUTH(self, courseid):
        """ GET request """
        # username = self.user_manager.session_username()
        # permissions = self.user_manager.has_staff_rights_on_course(course, username)
        course = self.get_course_and_check_rights(courseid, allow_all_staff=True)[0]
        users = self.user_manager.get_course_registered_users(course, False)
        tasks = course.get_tasks()
        data_users = []
        task_deadline = []
        task_no_deadline = []
        task_past_deadline = []
        order_tasks = []
        black_line = False
        task_start_line = ''

        """ Reorder course tasks according to deadline, no deadline and past deadline """
        for task in tasks:
            if tasks[task].get_deadline() == 'No deadline':
                task_no_deadline.append(tasks[task])
            else:
                current_task_datetime = datetime.strptime(tasks[task].get_deadline(), '%d/%m/%Y %H:%M:%S')
                now = datetime.now()

                if current_task_datetime < now:
                    task_past_deadline.append(tasks[task])

                    """ Check when to start the black line """
                    if not black_line:
                        task_start_line = tasks[task].get_name()
                        black_line = True
                else:
                    task_deadline.append(tasks[task])

        order_tasks = task_deadline + task_no_deadline + task_past_deadline

        """ Get all user tasks """
        for user in users:
            ordered_tasks_for_user = dict([(taskid.get_id(), {"taskid": taskid,
                                              "name": taskid.get_name(),
                                              "tried": 0,
                                              "status": "notviewed",
                                              "grade": 0}) for taskid in order_tasks])

            # TODO: Check if we can retrieve all users data once, then reference the needed details in the loop
            user_tasks = list(self.database.user_tasks.find({"username": user, "courseid": course.get_id()}))

            for user_task in user_tasks:
                if user_task["taskid"] in ordered_tasks_for_user:
                    ordered_tasks_for_user[user_task["taskid"]]["tried"] = user_task["tried"]
                    if user_task["tried"] == 0:
                        ordered_tasks_for_user[user_task["taskid"]]["status"] = "notattempted"
                    elif user_task["succeeded"]:
                        ordered_tasks_for_user[user_task["taskid"]]["status"] = "succeeded"
                    else:
                        ordered_tasks_for_user[user_task["taskid"]]["status"] = "failed"

                    ordered_tasks_for_user[user_task["taskid"]]["grade"] = user_task["grade"]
                    ordered_tasks_for_user[user_task["taskid"]]["submissionid"] = str(user_task["submissionid"])

            data_user = {'name': user, 'tasks': ordered_tasks_for_user}
            data_users.append(data_user)

        return self.template_helper.get_custom_renderer('frontend/webapp/plugins/matrix')\
            .admin(course, data_users, order_tasks, task_start_line)


def add_admin_menu(course):
    """ Add matrix setting to the admin panel """
    return ('matrix', '<i class="fa fa-graduation-cap fa-fw"></i>&nbsp; Matrix')


def add_css_file():
    """ Add matrix css file to the admin page """
    return web.ctx.homepath + '/static/webapp/plugins/matrix/matrix.css'


def init(plugin_manager, _, _2, _3):
    """ Init the plugin """
    plugin_manager.add_hook('course_admin_menu', add_admin_menu)
    plugin_manager.add_hook('css', add_css_file)
    plugin_manager.add_page("/admin/([^/]+)/matrix", MatrixPage)

