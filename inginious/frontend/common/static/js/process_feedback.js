var COMMENTS_IMAGES = {
    output: "/static/common/images/side-comments/output.png",
        input: "/static/common/images/side-comments/input.png",
        false_: "/static/common/images/side-comments/false.png",
};


function fillModalTerminalBoxes(feedbackData, scenarioId) {
    var scenarioIdStr = '-' + scenarioId;
    var comments = [];
    console.log('scenarioIdStr is ' + scenarioIdStr);
    console.log('feedbackData is ');
    console.log(feedbackData);

    // The modal's Terminal initialization
    var command_line = "C:\\Magshimim> program.exe";
    for (var i = 0; i < feedbackData.args.length; i++) {
        command_line += " " + feedbackData.args[i];
    }
    $("#scenario_log" + scenarioIdStr).append('<li>' + command_line + '<li>');

    for (var i = 0; i < feedbackData.log.quotes.length; i++) {
        var line = $('<li></li>');
        line.text(feedbackData.log.quotes[i].value);
        // todo, return this if
        if (feedbackData.log.quotes[i].type.en == "input" || feedbackData.log.quotes[i].type.en == "output") {
            console.log('inside input output ');
            line.addClass("commentable-section");
            line.attr("data-section-id", i.toString());

            comments.push({
                "sectionId": i.toString(),
                "comments": [
                    {
                        "id": i.toString(),
                        "authorAvatarUrl": COMMENTS_IMAGES[feedbackData.log.quotes[i].type.en],
                        "authorName": feedbackData.log.quotes[i].type.he,
                        "comment":  feedbackData.log.quotes[i].name
                    }
                ]
            });
        }
        console.log('append line');
        console.log(line);
        $("#scenario_log" + scenarioIdStr).append(line);
    }

    if (!feedbackData.result.bool) {
        var line = $('<li></li>');
        line.html("<br>");
        line.addClass("commentable-section");
        line.attr("data-section-id", "feedback");

        comments.push({
            "sectionId": "feedback",
            "comments": [
                {
                    "id": "feedback",
                    "authorAvatarUrl": COMMENTS_IMAGES[feedbackData.result.bool.toString() + "_"],
                    "authorName": feedbackData.result.text,
                    "comment": feedbackData.feedback.text
                }
            ]
        });
        console.log('append in g inside feedbackData.result.bool');
        console.log(line);
        $("#scenario_log" + scenarioIdStr).append(line);

    }


    var currentUser = {
        "id": 4,
        "avatarUrl": "support/images/user.png",
        "authorUrl": "http://google.com/",
        "name": "You"
    };

    console.log('comments for ' + scenarioIdStr);
    console.log(comments);

    var SideComments = require('side-comments');
    window.sideComments = new SideComments('#commentable-container' + scenarioIdStr, currentUser, comments);
}


function renderScenarioRows(feedbackData){
    var scenario_row,
        modal;
    console.log('here is feedbackData. ');
    console.log(feedbackData);

    $.each(feedbackData, function(id, data) {{
        console.log('here is feedbackData. data is -- ');
        console.log(data);
        console.log(id);
        data.id = id;
        data.indexId = parseInt(id) + 1;
        if (isSuccess(data)){{
            data.color = 'red'
        }}else{{
            data.color = 'green'
        }}
        //add the hidden modal
        modal = $(tmpl('tmpl-modal', data));
        $('body').append(modal);

        // add row to scenario table
        scenario_row = $(tmpl('tmpl-scenario-row', data));
        $('#scenarios-table').append(scenario_row);

    }});
}


// whether a scenario is success or failure
function isSuccess(data) {{
    return data.feedback
}}
