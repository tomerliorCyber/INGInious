import web
from collections import OrderedDict
from inginious.frontend.webapp.pages.course_admin.utils import INGIniousAdminPage
import json
from inginious.frontend.common.task_page_helpers import submission_to_json, list_multiple_multiple_choices_and_files
from bson.objectid import ObjectId

""" Manual plugin - show overall feedback about student """
class ManualPlugin(INGIniousAdminPage):
    """ Get all information about the users """
    def get_users(self, course):
        users = sorted(list(
            self.user_manager.get_users_info(self.user_manager.get_course_registered_users(course, False)).items()),
            key=lambda k: k[1][0] if k[1] is not None else "")

        users = OrderedDict([(user[0], {"username": user[0],
                                        "realname": user[1][0] if user[1] is not None else None}) for user in users])

        return users

    """ Get all lessons """
    def get_lessons(self, course):
        tasks = course.get_tasks()
        lessons_list = set()

        for task in tasks:
            lessons_list.add(task.split('-')[0])

        lessons = OrderedDict([(lesson, {"name": lesson,
                                         "tasks": []}) for lesson in sorted(lessons_list, key=int)])

        for task in tasks:
            lesson_num = task.split('-')[0]
            task_num = task.split('-')[1]

            lessons[lesson_num]['tasks'].append({"id": task_num,
                                                 "taskid": tasks[task]})

        return lessons
    """ Get next and back buttons """
    def get_buttons(self, current_user, users):
        len_users = len(list(users))

        if len_users <= 0 or current_user not in users:
            return None

        prev_user = list(users).index(current_user) - 1
        next_user = list(users).index(current_user) + 1

        back = list(users)[list(users).index(current_user) - 1] \
            if int(prev_user) >= 0 and prev_user < len_users else current_user
        next = list(users)[list(users).index(current_user) + 1] \
            if next_user < len_users else current_user

        return {"next": next, "back": back}


class IndexPage(ManualPlugin):
    def GET_AUTH(self, courseid):
        course = self.get_course_and_check_rights(courseid, allow_all_staff=True)[0]
        users = self.get_users(course)
        lessons = self.get_lessons(course)
        current_user = users[list(users)[0]]['username'] if len(list(users)) > 0 else None
        current_lesson = list(lessons)[0] if len(list(lessons)) > 0 else None
        buttons = self.get_buttons(current_user, users)
        user_data = dict()

        user_task = list(self.database.user_tasks.find({"courseid": course.get_id(), "username": current_user}))

        if user_task is not None:
            for task in user_task:
                submission = self.submission_manager.get_submission(task['submissionid'], False)
                submission = self.submission_manager.get_input_from_submission(submission)
                submission = self.submission_manager.get_feedback_from_submission(submission, show_everything=True)

                user_data[task['taskid'].split('-')[1]] = submission

        return self.template_helper.get_custom_renderer('frontend/webapp/plugins/manual')\
            .admin(course, lessons, users, current_lesson, current_user, buttons, self.webterm_link, user_data)


class StudentPage(ManualPlugin):
    def GET_AUTH(self, courseid, lesson_id, student_id):
        course = self.get_course_and_check_rights(courseid, allow_all_staff=True)[0]
        lessons = self.get_lessons(course)
        users = self.get_users(course)
        current_lesson = lesson_id
        current_user = student_id
        buttons = self.get_buttons(current_user, users)
        user_data = dict()

        user_task = list(self.database.user_tasks.find({"courseid": course.get_id(), "username": current_user}))

        if user_task is not None:
            for task in user_task:
                submission = self.submission_manager.get_submission(task['submissionid'], False)
                submission = self.submission_manager.get_input_from_submission(submission)
                submission = self.submission_manager.get_feedback_from_submission(submission, show_everything=True)

                user_data[task['taskid'].split('-')[1]] = submission

        if student_id not in users or lesson_id not in lessons:
            return web.seeother(web.ctx.homepath + '/admin/' + course.get_id() + '/manual')
        else:
            return self.template_helper.get_custom_renderer('frontend/webapp/plugins/manual') \
                .admin(course, lessons, users, current_lesson, current_user, buttons, self.webterm_link, user_data)


class TaskPage(INGIniousAdminPage):
    def set_selected_submission(self, course, task, submissionid):
        submission = self.submission_manager.get_submission(submissionid)
        is_staff = self.user_manager.has_staff_rights_on_course(course, self.user_manager.session_username())

        # Do not enable submission selection after deadline
        if not task.get_accessible_time().is_open() and not is_staff:
            return False

        # Check if task is done per group/team
        if task.is_group_task() and not is_staff:
            group = self.database.aggregations.find_one(
                {"courseid": task.get_course_id(), "groups.students": self.user_manager.session_username()},
                {"groups": {"$elemMatch": {"students": self.user_manager.session_username()}}})
            students = group["groups"][0]["students"]
        else:
            students = [self.user_manager.session_username()]

        # Check if group/team is the same
        if students == submission["username"]:
            self.database.user_tasks.update_many(
                {"courseid": task.get_course_id(), "taskid": task.get_id(), "username": {"$in": students}},
                {"$set": {"submissionid": submission['_id'],
                          "grade": submission['grade'],
                          "succeeded": submission["result"] == "success"}})
            return True
        else:
            return False

    def POST_AUTH(self, courseid, taskid):
        username = self.user_manager.session_username()

        try:
            course = self.course_factory.get_course(courseid)
            task = course.get_task(taskid)

            is_staff = self.user_manager.has_staff_rights_on_course(course, username)
            is_admin = self.user_manager.has_admin_rights_on_course(course, username)

            userinput = web.input()
            if "@action" in userinput and userinput["@action"] == "submit":
                # Verify rights
                if not self.user_manager.task_can_user_submit(task, username):
                    return json.dumps({"status": "error", "text": "You are not allowed to submit for this task."})

                # Reparse user input with array for multiple choices
                init_var = list_multiple_multiple_choices_and_files(task)
                userinput = task.adapt_input_for_backend(web.input(**init_var))

                if not task.input_is_consistent(userinput, self.default_allowed_file_extensions,
                                                self.default_max_file_size):
                    web.header('Content-Type', 'application/json')
                    return json.dumps({"status": "error",
                                       "text": "Please answer to all the questions and verify the extensions of the files "
                                               "you want to upload. Your responses were not tested."})
                del userinput['@action']

                # Get debug info if the current user is an admin
                debug = is_admin
                if "@debug-mode" in userinput:
                    if userinput["@debug-mode"] == "ssh" and debug:
                        debug = "ssh"
                    del userinput['@debug-mode']

                # Start the submission
                try:
                    submissionid, oldsubids = self.submission_manager.add_job(task, userinput, False)
                    web.header('Content-Type', 'application/json')
                    return json.dumps({"status": "ok", "submissionid": str(submissionid), "remove": oldsubids})
                except Exception as ex:
                    web.header('Content-Type', 'application/json')
                    return json.dumps({"status": "error", "text": str(ex)})
            elif "@action" in userinput and userinput["@action"] == "check" and "submissionid" in userinput:
                result = self.submission_manager.get_submission(userinput['submissionid'])

                if result is None:
                    web.header('Content-Type', 'application/json')
                    return json.dumps({'status': "error"})
                elif self.submission_manager.is_done(result):
                    web.header('Content-Type', 'application/json')
                    result = self.submission_manager.get_input_from_submission(result)
                    result = self.submission_manager.get_feedback_from_submission(result, show_everything=is_staff)

                    # user_task always exists as we called user_saw_task before
                    user_task = self.database.user_tasks.find_one({
                        "courseid": task.get_course_id(),
                        "taskid": task.get_id(),
                        "username": self.user_manager.session_username()
                    })

                    submissionid = user_task.get('submissionid', None)
                    default_submission = self.database.submissions.find_one(
                        {'_id': ObjectId(submissionid)}) if submissionid else None
                    if default_submission is None:
                        self.set_selected_submission(course, task, userinput['submissionid'])
                    return submission_to_json(result, is_admin, False,
                                                  True if default_submission is None else default_submission['_id'] ==
                                                                                          result['_id'])
                else:
                    web.header('Content-Type', 'application/json')
                    if "ssh_host" in result:
                        return json.dumps({'status': "waiting",
                                           'ssh_host': result["ssh_host"],
                                           'ssh_port': result["ssh_port"],
                                           'ssh_password': result["ssh_password"]})
                    # Here we are waiting. Let's send some useful information.
                    waiting_data = self.submission_manager.get_job_queue_info(
                        result["jobid"]) if "jobid" in result else None
                    if waiting_data is not None:
                        nb_tasks_before, approx_wait_time = waiting_data
                        return json.dumps({'status': "waiting", 'nb_tasks_before': nb_tasks_before,
                                           'approx_wait_time': approx_wait_time})
                    return json.dumps({'status': "waiting"})
            elif "@action" in userinput and userinput["@action"] == "load_submission_input" and "submissionid" in userinput:
                submission = self.submission_manager.get_submission(userinput["submissionid"])
                submission = self.submission_manager.get_input_from_submission(submission)
                submission = self.submission_manager.get_feedback_from_submission(submission, show_everything=is_staff)
                if not submission:
                    raise web.notfound()
                web.header('Content-Type', 'application/json')
                return submission_to_json(submission, is_admin, True)
            elif "@action" in userinput and userinput["@action"] == "kill" and "submissionid" in userinput:
                self.submission_manager.kill_running_submission(userinput["submissionid"])  # ignore return value
                web.header('Content-Type', 'application/json')
                return json.dumps({'status': 'done'})
            elif "@action" in userinput and userinput["@action"] == "set_submission" and "submissionid" in userinput:
                web.header('Content-Type', 'application/json')
                if task.get_evaluate() != 'student':
                    return json.dumps({'status': "error"})

                if self.set_selected_submission(course, task, userinput["submissionid"]):
                    return json.dumps({'status': 'done'})
                else:
                    return json.dumps({'status': 'error'})
        except:
            if web.config.debug:
                raise
            else:
                raise web.notfound()


def add_admin_menu(course):
    """ Add matrix setting to the admin panel """
    return ('manual', '<i class="fa fa-list-ol fa-fw"></i>&nbsp; Manual Assessment')


def add_css_file():
    """ Add matrix css file to the admin page """
    return web.ctx.homepath + '/static/webapp/plugins/manual/manual.css'


def add_js_file():
    """ Add matrix css file to the admin page """
    return web.ctx.homepath + '/static/webapp/plugins/manual/manual.js'


def init(plugin_manager, _, _2, _3):
    plugin_manager.add_hook("course_admin_menu", add_admin_menu)
    plugin_manager.add_hook('javascript_header', add_js_file)
    plugin_manager.add_hook('css', add_css_file)
    plugin_manager.add_page("/admin/([^/]+)/manual", IndexPage)
    plugin_manager.add_page("/admin/([^/]+)/manual/([^/]+)/([^/]+)", StudentPage)
    plugin_manager.add_page("/admin/([^/]+)/task-manual/([^/]+)", TaskPage)


