function processFeedback(feedbackData, scenarioId) {
    var scenarioIdStr = '-' + scenarioId;
    var comments = [];
    console.log('scenarioIdStr is ' + scenarioIdStr);





    // The modal's Terminal initialization
    var command_line = "C:\\Magshimim> program.exe";
    for (var i = 0; i < feedbackData.args.length; i++) {
        command_line += " " + feedbackData.args[i];
    }
    $("#scenario_log" + scenarioIdStr).append("<li>" + command_line + "<li>");

    for (var i = 0; i < feedbackData.log.quotes.length; i++) {
        var line = $('<li></li>');
        line.text(feedbackData.log.quotes[i].value);

        // todo, return this if 
        // if (feedbackData.log.quotes[i].type.en == "input" || feedbackData.log.quotes[i].type.en == "output") {
            line.addClass("commentable-section");
            line.attr("data-section-id", i.toString());

            comments.push({
                "sectionId": i.toString(),
                "comments": [
                    {
                        "id": i.toString(),
                        "authorAvatarUrl": COMMENTS_IMAGES.input, //COMMENTS_IMAGES[feedbackData.log.quotes[i].type.en],
                        "authorName": feedbackData.log.quotes[i].type.he,
                        "comment":  "טקסט טקסט טקסט" //feedbackData.log.quotes[i].name
                    }
                ]
            });
        // }
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
                    "authorAvatarUrl": "http://f.cl.ly/items/0s1a0q1y2Z2k2I193k1y/default-user.png", //COMMENTS_IMAGES[feedbackData.result.bool.toString() + "_"],
                    "authorName": feedbackData.result.text,
                    "comment": feedbackData.feedback.text
                }
            ]
        });

        $("#scenario_log" + scenarioIdStr).append(line);

    }


    var currentUser = {
        "id": 4,
        "avatarUrl": "support/images/user.png",
        "authorUrl": "http://google.com/",
        "name": "You"
    };

    scenarioIdStr = '-1';
    window.comments = comments;
    window.div_to_search = '#commentable-container' + scenarioIdStr;
    
    var SideComments = require('side-comments');
    window.sideComments = new SideComments('#commentable-container' + scenarioIdStr, currentUser, comments);
}
