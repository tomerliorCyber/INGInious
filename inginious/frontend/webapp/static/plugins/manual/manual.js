$(document).ready(function() {
    onSubmitAllBtn();
    onToTopBtn();
});


/**
 * On submit all btn
 */
function onSubmitAllBtn() {
    var submitAllBtn = $('.submit-all');

    submitAllBtn.on('click', function(event) {
        event.preventDefault();
        $('.submit-btn').trigger('click');
    });
}


/**
 * On click to top btn
 */
function onToTopBtn() {
    var body = $('html, body');
    var toTopBtn = $('.to-top');

    toTopBtn.on('click', function(event) {
        event.preventDefault();
        body.stop().animate({ scrollTop: 0 }, '500', 'swing');
    });
}

/**
 * On click to feedback btn
 * @param task
 */
function onToFeedback(task) {
    var body = $('html, body');
    var taskDiv = $('.task-' + task);
    var toFeedbackBtn = $(taskDiv).find('.to-feedback');

    toFeedbackBtn.on('click', function() {
        event.preventDefault();
        $(body).stop().animate({ scrollTop: $(taskDiv).offset().top }, '500', 'swing');

    });
}

/**
 * Init manual task
 * @param taskId
 * @param lessonId
 * @param courseId
 */
function initManualTask(taskId) {
    var task = $('.task-' + taskId);
    var taskNumber = $('#task-submit-'  + taskId);
    var form = taskNumber.closest('form');

    form.on('submit', function(event) {
        event.preventDefault();
        var textareaInput = $($(this).find(".code-editor")).val();
        var url = $(this).attr('action');


        if (!manualTaskValidation(task)) {
            return;
        }

        $.ajax({
            url: url,
            method: "POST",
            data: { "program": textareaInput, "@action": "submit" },
            dataType: 'json',
            success: function(data) {
                if ("status" in data && data["status"] == "ok" && "submissionid" in data) {
                    manualWaitForSubmission(data['submissionid'], task);
                }
            },
            error: function(msg) {
                manualDisplayErrorAlert(task);
            }
        });
    });
}


/**
 * Wait for submission
 * @param submissionId
 * @param task
 */
function manualWaitForSubmission(submissionId, task) {
    var url = task.find('form').attr('action');

    setTimeout(function() {
        $.ajax({
            url: url,
            method: "POST",
            data: { "@action": "check", "submissionid": submissionId },
            dataType: 'json',
            success: function(data) {
                if ("status" in data && data['status'] == "waiting") {
                    manualWaitForSubmission(submissionId, task);
                    manualGetLoadingAlert(task);
                } else if("status" in data && "result" in data && "grade" in data) {
                    if (data['result'] == "failed") {
                        manualDisplayFailedAlert(task, data);
                    } else if (data['result'] == "success") {
                        manualDisplaySuccessAlert(task, data);
                    } else if (data['result'] == "timeout") {
                        manualDisplayTimeoutAlert(task);
                    } else if (data['result'] == "overflow") {
                        manualDisplayOverflowAlert(task);
                    } else if (data['result'] == "killed") {
                        manualDisplayKillAlert(task);
                    } else { // error
                        manualDisplayErrorAlert(task);
                    }
                } else {
                    manualDisplayErrorAlert(task);
                }
            },
            error: function(data) {
                manualDisplayErrorAlert(task);
            }
        });
    }, 1000);
}


/**
 * Check if the form is valid or not
 * @param form
 * @returns {boolean}
 */
function manualTaskValidation(task) {
    var form = task.find('form');
    var textareaInput = form.find(".code-editor");

    // Check if textarea is empty or not
    if (!textareaInput.val()) {
        var span = $('<span></span>');
        span.html('Please answer to all the questions.');
        var taskAlert = manualGetAlertCode(span, 'danger');

        task.find('#task_alert').html(taskAlert);

        return false;
    } else {
        return true;
    }
}


/**
 * Get alert code
 * @param content
 * @param type
 * @returns {*|jQuery|HTMLElement}
 */
function manualGetAlertCode(content, type) {
    var taskAlert = $('<div></div>');
    taskAlert.attr('id', 'task_alert');

    var alert = $('<div></div>');
    alert.addClass('alert fade in alert-' + type);
    alert.attr('role', 'alert');
    alert.appendTo(taskAlert);

    content.appendTo(alert);

    return taskAlert;
}


/**
 * Get loading alert
 * @param task
 */
function manualGetLoadingAlert(task) {
    var form = task.find('form');
    var content = '<i class="fa fa-spinner fa-pulse fa-fw" aria-hidden="true"></i>';
    content += "<b>Your submission has been sent...</b>";

    var loadingAlert = $('<div></div>');
    loadingAlert.addClass('loading-alert');
    loadingAlert.html(content);

    var taskAlert = manualGetAlertCode(loadingAlert, 'info');

    task.find('#task_alert').html(taskAlert);
}


/**
 * Display failed alert
 * @param task
 * @param taskData
 */
function manualDisplayFailedAlert(task, taskData) {
    var div = $('<div></div>');

    var b = $('<b></b>');
    b.html('There are some errors in your answer. Your score is ' + taskData.grade + '<br>');
    b.appendTo(div);

    var pre = $(taskData.text);
    pre.appendTo(div);

    var taskAlert = manualGetAlertCode(div, 'danger');

    task.find('#task_alert').html(taskAlert);
}


/**
 * Display success alert
 * @param task
 * @param taskData
 */
function manualDisplaySuccessAlert(task, taskData) {
    var para = $('<p></p>');
    para.html('Your answer passed the tests! Your score is ' + taskData.grade);

    var taskAlert = manualGetAlertCode(para, 'success');

    task.find('#task_alert').html(taskAlert);
}


/**
 * Display kill alert
 * @param task
 */
function manualDisplayKillAlert(task) {
    var b = $('<b></b>');
    b.html('Your submission was killed.');

    var taskAlert = manualGetAlertCode(b, 'warning');

    task.find('#task_alert').html(taskAlert);
}


/**
 * Display error alert
 * @param task
 */
function manualDisplayErrorAlert(task) {
    var b = $('<b></b>');
    b.html('An internal error occured. Please retry later. If the error persists, send an email to the course administrator.');

    var taskAlert = manualGetAlertCode(b, 'danger');

    task.find('#task_alert').html(taskAlert);
}


/**
 * Display timeout alert
 * @param task
 * @param taskData
 */
function manualDisplayTimeoutAlert(task) {
    var b = $('<b></b>');
    b.html('Your submission timed out');

    var taskAlert = manualGetAlertCode(b, 'warning');

    task.find('#task_alert').html(taskAlert);
}


/**
 * Display overflow alert
 * @param task
 * @param taskData
 */
function manualDisplayOverflowAlert(task) {
    var b = $('<b></b>');
    b.html('Your submission made an overflow');

    var taskAlert = manualGetAlertCode(b, 'warning');

    task.find('#task_alert').html(taskAlert);
}