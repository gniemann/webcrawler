/**
 * xmlrequests.js
 *
 * Author: Ashton Herrington
 * Last modified date: 07/22/16
 *
 * Purpose: To create and send xml requests that initialize the crawl as well as provide
 * long polling to gather results afterwards
 */

//set of global shared variables
var postResponse;
var jobId;
var nodeMap = [];
var xmlHttp = createXmlHttpRequestObject();
var xmlHttp2 = createXmlHttpRequestObject();

//important variable, determines if the crawl has begun or not
var started = false;

//When the submit "crawl" from the form is pressed, this in combination with stopSubmit prevents redirect
$(document).ready(function () {
    var submitButton = document.getElementById("submitpic");
    submitButton.addEventListener('click', stopSubmit, false);
});

//Stops form submission, checks form validity, and alters view as needed
function stopSubmit(evt) {
    evt.preventDefault();
    var isValid = $("#crawl").parsley().validate();
    if (isValid) {
        process();
    } else {
        if (!$('#type_data').parsley().isValid()) {
            $("#spacer1").html('');
        }
        if (!$('#url_data').parsley().isValid()) {
            $("#spacer2").html('');
        }
    }
}

//Code previously written by me in CS290 to create AJAX results
function createXmlHttpRequestObject() {

    var xmlHttp;

    //test to determine if the window is Active X
    if (window.ActiveXObject) {
        try {
            xmlHttp = new ActiveXObject("Microsoft.XMLHTTP");
        } catch (e) {
            xmlHttp = false;
        }

    }
    //otherwise a XMLHTTPRequest object is created
    else {
        try {
            xmlHttp = new XMLHttpRequest();
        } catch (e) {
            xmlHttp = false;
        }
    }
    //if an error occurs it is presented to the user
    if (!xmlHttp)
        alert("Error processing XML Http Request object.");
    //and finally the function returns the newly created object
    else
        return xmlHttp;
}

//process the AJAX request
function process() {

    //confirmation that state is valid before taking action
    if (xmlHttp.readyState == 0 || xmlHttp.readyState == 4) {

        //grab the variables of interest from the form 
        var url = document.forms["crawl"]["url"].value;
        var searchType = document.forms["crawl"]["search_type"].value;
        var maxResults = document.forms["crawl"]["max_results"].value;
        var searchTerm = document.forms["crawl"]["search_term"].value;

        //dynamically create a params string from these variables
        var params = "start_page=" + url + "&";
        params += "search_type=" + searchType + "&";
        params += "depth=" + maxResults + "&";
        params += "end_phrase=" + searchTerm;

        var savedCookies = getCookie('gammacrawler');
        if (savedCookies != null) {
            cookieArray = JSON.parse(savedCookies);
        }
        var savedSearch = [url, searchType, maxResults, searchTerm, Date.now()];
        cookieArray.push(savedSearch);

        cookieArray.sort( 
            function(a, b) {
                // sort in descending order by date
                if(a[4] == undefined) return 1;
                if(b[4] == undefined) return -1;
                return b[4] - a[4];
            });

        // remove duplicate cookies
        var cookieSet = {}
        var uniqueCookies = []
        for (var i = 0; i < cookieArray.length; i++) {
            var key = JSON.stringify(cookieArray[i].slice(0, 4));
            if (!cookieSet[key]) {
                uniqueCookies.push(cookieArray[i]);
                cookieSet[key] = true;
            }
        }
        cookieArray = uniqueCookies;
        cookieSet = undefined;

        // store save cleaned cookie array
        var jsonCookie = JSON.stringify(cookieArray);
        setCookie('gammacrawler', jsonCookie, 14);

        //post the string to the crawler to begin the crawl
        xmlHttp.open("POST", "https://gammacrawler.appspot.com/crawler", true);
        xmlHttp.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
        xmlHttp.setRequestHeader("Access-Control-Allow-Origin", "*");
        xmlHttp.onreadystatechange = handleTheServerResponse;
        xmlHttp.send(params);
    } else {
        setTimeout('process()', 1000);
    }

    function handleTheServerResponse() {
        //first checks that the conditions are good
        if (xmlHttp.readyState == 4) {
            if (xmlHttp.status == 200) {
                var theResponse = xmlHttp.responseText;
                postResponse = JSON.parse(theResponse);
                if (postResponse && postResponse['status'] != 'failure') {
                    //information from crawler is received in return: jobId, and rootNode stats
                    jobId = postResponse['job_id'];
                    var rootId = postResponse['root']['id'];
                    var rootNode = postResponse['root'];
                    nodeMap[rootId] = rootNode;

                    //rootNode is added to the physics engine
                    physicsEngine.addNode(rootNode['id'], null);
                    //at this point we start the simulation
                    if (!started) {
                        // physicsEngine.runSimulation();
                        started = true;
                    }
                    addNode(
                        physicsEngine.provideCoordinates(rootNode['id']).px,
                        physicsEngine.provideCoordinates(rootNode['id']).py,
                        rootNode['url'],
                        rootNode['id'],
                        null,
                        rootNode['favicon'], 1.6
                    );
                    //remove the form, replace it with the interactive map
                    //$('#form').css({visibility: 'hidden', position: 'absolute', top: 0, left: 0});
                    $('#form').css({display: 'none'});
                    //$('#graph').css({visibility: 'visible'});
                    $('#graph').css({display: 'block'});
                    $(document).keyup(toggleFullscreen);
                    //begin polling for further nodes acquired by the crawl
                    pollCrawlResults();
                    doResize(); // force the display area to resize
                } else if (postResponse['status'] == 'failure' && postResponse['errors'][0][0] == 'Invalid input.') {
                    alert('Invalid URL, please check format and try again.');
                }
            } else {
                console.log(xmlHttp.status);
                alert('Something went wrong');
            }
        }
    }
}

//Every second, poll the API to see if mode nodes have been acquired by the crawler
function pollCrawlResults() {

    //url of the crawler, requires job ID provided as return value for beginning crawl
    var getUrl = "https://gammacrawler.appspot.com/crawler/" + jobId;

    //checks to see a valid state prior to initializing the crawl
    if (xmlHttp2.readyState == 0 || xmlHttp2.readyState == 4) {
        xmlHttp2.open("GET", getUrl, true);
        xmlHttp2.onreadystatechange = retrieveCrawlResults;
        xmlHttp2.send();
    } else {
        setTimeout('pollCrawlResults()', 1000);
    }

    //retrieves the results of the crawl from the API 
    function retrieveCrawlResults() {

        if (xmlHttp2.readyState == 4) {
            if (xmlHttp2.status == 200) {
                //parse the response in JSON format
                var theResponse = JSON.parse(xmlHttp2.responseText);
                crawlNodes = theResponse;
                //cycle through each of the new nodes found
                theResponse['new_nodes'].forEach(function (node) {

                    //add the node to the nodemap and physics engine
                    nodeMap[node['id']] = node;
                    physicsEngine.addNode(node['id'], node['parent']);
                    addNode(
                        physicsEngine.provideCoordinates(node['id']).px,
                        physicsEngine.provideCoordinates(node['id']).py,
                        node['url'],
                        node['id'],
                        node['parent'],
                        node['favicon'], 1
                    );
                    if (node['phrase_found']) {
                        alert('Termination phrase encountered at ' + node['url'])
                    }
                });
                //if the API declares the crawl isn't finished, poll again in 2 seconds
                if (!theResponse['finished']) {
                    setTimeout('pollCrawlResults()', 2000);
                } else {
                    //otherwise, display the back button allowing the user to start a new crawl
                    //$('#backButton').css("visibility", "visible");
                    $('#backButton').css({display: 'block'});
                }
            } else {
                //wait another second if needed under this condition
                if (xmlHttp2.status == 404 && crawlNodes == null) {
                    setTimeout('pollCrawlResults()', 1000);
                } else {
                    //error condition, inform user
                    console.log(xmlHttp.status);
                    alert('Something went wrong');
                }
            }
        }
    }
}



