function processFeedback(feedbackData, scenarioId) {
    var scenarioIdStr = '-' + scenarioId;
    var comments = [];
    console.log('scenarioIdStr is ' + scenarioIdStr);


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
                        "authorAvatarUrl": COMMENTS_IMAGES[feedbackData.log.quotes[i].type.en],
                        "authorName": feedbackData.log.quotes[i].type.he,
                        "comment": feedbackData.log.quotes[i].name
                    }
                ]
            });
        // }
    }


    var currentUser = {
        "id": 4,
        "avatarUrl": "support/images/user.png",
        "authorUrl": "http://google.com/",
        "name": "You"
    };

    var SideComments = require('side-comments');
    window.sideComments = new SideComments('#commentable-container' + scenarioIdStr, currentUser, comments);
}
