var xmlHttp = createXmlHttpRequestObject();
var xmlHttp2 = createXmlHttpRequestObject();

//set of global shared variables
var postResponse;
var jobId;
var nodeMap = [];

$(document).ready(function () {
    var submitButton = document.getElementById("submitpic");
    submitButton.addEventListener('click', stopSubmit, false);
});

function stopSubmit(evt) {
    evt.preventDefault();
}

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

var started = false;

function process() {
    
    //confirmation that state is valid before taking action
    if (xmlHttp.readyState == 0 || xmlHttp.readyState == 4) {
        
        var url = document.forms["crawl"]["url"].value;
        var searchType = document.forms["crawl"]["search_type"].value;
        var maxResults = document.forms["crawl"]["max_results"].value;
        var searchTerm = document.forms["crawl"]["search_term"].value;
        
        var params = "start_page=" + url + "&";
        params += "search_type=" + searchType + "&";
        params += "depth=" + maxResults + "&";
        params += "end_phrase=" + searchTerm;
        
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
                if (postResponse) {
                    jobId = postResponse['job_id'];
                    var rootId = postResponse['root']['id'];
                    var rootNode = postResponse['root'];
                    nodeMap[rootId] = rootNode;
                    
                    physicsEngine.addNode(rootNode['id'], null);
                    if (!started) {
                        physicsEngine.runSimulation();
                        started = true;
                    }
                    addNode(
                        physicsEngine.provideCoordinates(rootNode['id']).px,
		       physicsEngine.provideCoordinates(rootNode['id']).py,
		       rootNode['url'], 
		       rootNode['id'] 
                    );
                    $('#form').css("visibility", "hidden");
                    $('#demo').css("visibility", "visible");
                    pollCrawlResults();
                }
            } else {
                console.log(xmlHttp.status);
                alert('Something went wrong');
            }
        }
    }
}

function pollCrawlResults() {
    
    var getUrl = "https://gammacrawler.appspot.com/crawler/" + jobId;
    
    if (xmlHttp2.readyState == 0 || xmlHttp2.readyState == 4) {
        xmlHttp2.open("GET", getUrl, true);
        //xmlHttp2.setRequestHeader("Access-Control-Allow-Origin", "*");
        xmlHttp2.onreadystatechange = retrieveCrawlResults;
        xmlHttp2.send();
    } else {
        setTimeout('pollCrawlResults()', 1000);
    }
    
    function retrieveCrawlResults() {
        
        if (xmlHttp2.readyState == 4) {
            if (xmlHttp2.status == 200) {
                var theResponse = JSON.parse(xmlHttp2.responseText);
                crawlNodes = theResponse;
                theResponse['new_nodes'].forEach(function (node) {
                    nodeMap[node['id']] = node;
                    
                    physicsEngine.addNode(node['id'], node['parent']);
                    
                    addNode(
                        physicsEngine.provideCoordinates(node['id']).px,
                        physicsEngine.provideCoordinates(node['id']).py,
                        node['url'], 
                        node['id'], 
                        node['parent']
                    );
                });
                if (!theResponse['finished']) {
                    setTimeout('pollCrawlResults()', 2000);
                } else {
                    $('#backButton').css("visibility", "visible");
                }
            } else {
                if (xmlHttp2.status == 404 && crawlNodes == null) {
                    setTimeout('pollCrawlResults()', 1000);
                } else {
                    console.log(xmlHttp.status);
                    alert('Something went wrong');
                }
            }
        }
    }
}



