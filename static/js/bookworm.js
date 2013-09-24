(function(){
// Spinner from http://fgnass.github.io/spin.js/
  var opts = {
    lines: 8, // The number of lines to draw
    length: 5, // The length of each line
    width: 7, // The line thickness
    radius: 15, // The radius of the inner circle
    corners: 1, // Corner roundness (0..1)
    rotate: 0, // The rotation offset
    direction: 1, // 1: clockwise, -1: counterclockwise
    color: '#7e7377', // #rgb or #rrggbb or array of colors
    speed: 0.9, // Rounds per second
    trail: 72, // Afterglow percentage
    shadow: true, // Whether to render a shadow
    hwaccel: false, // Whether to use hardware acceleration
    className: 'spinner', // The CSS class to assign to the spinner
    zIndex: 2e9, // The z-index (defaults to 2000000000)
    top: 'auto', // Top position relative to parent in px
    left: 'auto' // Left position relative to parent in px
  };

//Upon the user clicking the submit button, get the values that the user entered.   
   $("#user-input").submit(function(event){
        //Prevent the page from reloading.
        event.preventDefault();
      //Check that it's a valid 5-digit code.
      var zipcode = $("#zipcode").val();
      if (zipcode.length !== 5 || isNaN(zipcode) == true) {
        $("#warnings").html("Please enter a valid five-digit zip code.");
      } else {
        $("h1").hide();
        $("h3").html("Please wait: the Social Bookworm is burrowing through your friends' bookshelves.");
        $("top-margin").append("<h4>If you have a lot of friends with huge bookshelves, this might take awhile.</h4>");
        $("#warnings").hide();
        $("#user-input").hide();  
        var spinner = new Spinner(opts).spin(document.getElementById('spinner'));
        fetchUserData(zipcode);
      }
   });

    function changeText(image, friend, title, date, link, venue, city, address) {
        $("h3").html("Your results:");
        var changeable = $(".display")[0];
        var myText = "<img class='avatar' src='" + image + "'> Your friend <b>" + friend + "</b> might be interested in attending: <h4><a href = '" + link + "'>" + title + "</a></h4><h5>" + date + "</h5>" + "<p>" + venue + "<br>" + address + "<br>" + city + "</p>";
        $(changeable).append("<div class='result'>" + myText + "</div>");
    };

    function noResults() {
        $("h3").html("Your results:");
        var changeable = $(".no-results");
        var myText = "Unfortunately, the worms did not find any event matches. Please check back next month!"
        $(changeable).append("<div class='.no-results'>" + myText + "</div>");
    };

   function fetchUserData(zip) {
      var address = "/goodreads/" + zip;
      var results = jQuery.get(address, function() {})
        .fail(function() { alert("error"); })
      .done(function() { 
        console.log("success!");
        $("#user-input").hide();
        $("#spinner").hide();
        data = results.responseText;
        if (data == "No results found.") {
          console.log("nada");
          noResults();
          return "None";
        }
        jsonData = JSON.parse(data);
        for (item in jsonData) {
          var event_link = jsonData[item].author_event.event_link,
              event_title = jsonData[item].author_event.event_title,
              event_datetime = jsonData[item].author_event.date,
              friend_name = jsonData[item].friend.friend_name,
              friend_image = jsonData[item].friend.image,
              event_venue = jsonData[item].author_event.venue,
              event_city = jsonData[item].author_event.city,
              event_address = jsonData[item].author_event.address,
              date = new Date(event_datetime);
          changeText(friend_image, friend_name, event_title, date, event_link, event_venue, event_city, event_address);
        }
      })
   }
}());