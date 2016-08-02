/*
 * main.js
 *
 * Author: Ashton Herrington
 * Last modified date: 08/01/16
 *
 * Purpose: This file both acts as the scaffold that connects the physics and graphics engines, as well
 * as the graphics engine itself.
 */

// define a few globals here
var graphicsEngine;
var renderer = null;
var renderWidth = 800;
var renderHeight = 600;
var tilemap = null;
var ySize;
var xSize;
var currentParentId = null;
var currentUrl;
var currentSprite;
var graphicsMap = [];
var graphics = new PIXI.Graphics();

var cookieArray = [];

//this is used to create the dynamically positioned URL sprite
var popupText = new PIXI.Text('', { font: '36px Arial', fill: 0xff1010, align: 'center' });
popupText.on('mousedown', takeHyperlink);
popupText.interactive = true;
popupText.buttonMode = true;

//On window load, calculate the size of the window the graphics engine has available to it 
window.onload = function () {
    
    var offset = $('#demo').offset();
    ySize = $(window).height() - offset.top - 30;
    xSize = $(window).width() - 80;
    
    graphicsEngine = new Main('', xSize, ySize);
    $('#demo').append(graphicsEngine);


    var savedCookies = getCookie('gammacrawler');
    if (savedCookies != null) {
       cookieArray = JSON.parse(savedCookies);
       cookieArray.sort( 
        function(a, b) {
            // sort in descending order by date
            if(a[4] == undefined) return 1;
            if(b[4] == undefined) return -1;
            return b[4] - a[4];
            });
    }
    var oldSearchs = document.getElementById("previous_search");
    if (cookieArray.length == 0){
       oldSearchs.style.visibility = 'hidden';
       document.getElementById("loadPreviousSearch").style.visibility = 'hidden';
    }
    
    var defaultOption = document.createElement("option");
    defaultOption.textContent = '  ';
    defaultOption.value = -1;
    oldSearchs.appendChild(defaultOption);
    for(var i = 0; i < cookieArray.length; i++) {
       var option = cookieArray[i];
       var newOption = document.createElement("option");
       var maxResults = option[1] == 'DFS' ? 'Max Results' : 'Search Depth';
       newOption.textContent = "URL: " + option[0] + ' Search Type: ' + option[1] + ' ' + maxResults + ": " + 
	  option[2] + ' Search term: ' + option[3];
       newOption.value = i;
       oldSearchs.appendChild(newOption);
    } 
}

//Fills the form based on the contents of the previous search dropdown menu
function fillForm(value) {
   if (value == -1) {     
      document.forms["crawl"]["url"].value = '';
      document.forms["crawl"]["search_type"].value = 'DFS';
      $('#search_type').html('Max results:');
      document.forms["crawl"]["max_results"].value = '';
      document.forms["crawl"]["search_term"].value = '';
   } else {
      document.forms["crawl"]["url"].value = cookieArray[value][0];
      document.forms["crawl"]["search_type"].value = cookieArray[value][1];
      document.forms["crawl"]["max_results"].value = cookieArray[value][2];
      document.forms["crawl"]["search_term"].value = cookieArray[value][3];
   }
}

//Function that gets cookies, provided by www.w3schools.com/js/js_cookies.asp
function getCookie(cookieName) {
   var name = cookieName + "=";
   var cookieArray =  document.cookie.split(';');
   for(var i = 0; i < cookieArray.length; i++) {
      var c = cookieArray[i];
      while (c.charAt(0) == ' ') {
         c = c.substring(1);
      }
      if (c.indexOf(name) == 0) {
         return c.substring(name.length, c.length);
      }
   }
} 

//Function that sets cookies, provided by www.w3schools.com/js/js_cookies.asp
function setCookie(cname, cvalue, exdays) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires="+ d.toUTCString();
    document.cookie = cname + "=" + cvalue + "; " + expires;
}


//initialize physicsEngine, defined in Jason's classes and set its display scale
var physicsEngine = new SimulationRefactorInterface();
//physicsEngine.setDisplayScale(18400, 16000, 15);
physicsEngine.setDisplayScale(32000, 16000, 15);

//Changes the contents of the form to show search depth or max results based on search chosen
function switchType(value) {
    if (value == 'BFS') {
        $('#search_type').html('Search depth:');
	$('#type_data').attr("data-parsley-range", "[1,4]")
    } else {
        $('#search_type').html('Max results:');
	$('#type_data').attr("data-parsley-range", "[1,1000]")
    }
}

//Wrapper that interfaces with graphics engine to update node coordinates after calculations
function receiveCoordinates(nodeArray) {
    
    nodeArray.forEach(addOrUpdateNode);
    
    function addOrUpdateNode(item, index, array) {
        //this means that the node is not currently tracked
        if (typeof graphicsMap[item.id] === 'undefined') {
            addNode(item.px, item.py, nodeMap[index].url, item.id, nodeMap[index].parent);
        } else {
            graphicsMap[item.id][0].position.x = item.px;
            graphicsMap[item.id][0].position.y = item.py;
        }
    }
}

//Add a node to be tracked (by the graphics engine, not physics engine)
function addNode(x, y, url, id, parentId, favicon) {
    
    var texture;

    if (favicon) {
        texture = PIXI.Texture.fromImage(favicon);
    } else {
        texture = PIXI.Texture.fromImage("images/sunburst.png");
    }
    
    //originally the sprite were bunnies, kept this for kicks :)
    var bunny = new PIXI.Sprite(texture);
    bunny.anchor.x = 0.5;
    bunny.anchor.y = 0.5;
    bunny.position.x = x;
    bunny.position.y = y;
    bunny.height = 100;
    bunny.width = 100;
    bunny.interactive = true;
    bunny.buttonMode = true;
    bunny
     // events for drag start
     .on('mousedown', onDragStart)
     .on('touchstart', onDragStart)
     // events for drag end
     .on('mouseup', onDragEnd)
     .on('mouseupoutside', onDragEnd)
     .on('touchend', onDragEnd)
     .on('touchendoutside', onDragEnd)
     // events for drag move
     .on('mousemove', onDragMove)
     .on('touchmove', onDragMove)
     .on('mouseover', onMouseover);
    
    graphicsMap[id] = [bunny, url, parentId];
    var hiddenId = new PIXI.Text(id);
    hiddenId.visible = false;
    bunny.addChild(hiddenId);
    currentParentId = parentId;
    tilemap.addChild(bunny);
}

//Canvas is defined
function Main(tilesPath, w, h) {
    
    //allow defaulting modes if width and height are not set in constructor
    PIXI.scaleModes.DEFAULT = PIXI.scaleModes.NEAREST;
    stage = new PIXI.Stage(0x888888);
    if (w != 0 && h != 0) {
        renderWidth = w;
        renderHeight = h;
    }
    //use PIXIjs framework for renderer and image loader
    renderer = PIXI.autoDetectRenderer(renderWidth, renderHeight);
    var tileAtlas = [tilesPath + "tiles.json"];
    var loader = PIXI.loader;
    loader.add(tileAtlas);
    loader.once('complete', onLoaded);
    loader.load();
    return renderer.view;
   
    //call back that occurs once the PIXI loader loads the canvas/renderer 
    function onLoaded() {
        
        tilemap = new Tilemap(251, 251);
        stage.addChild(tilemap);
        
        // zoom in on the starting tile
        tilemap.selectTile(tilemap.startLocation.x, tilemap.startLocation.y);
        tilemap.zoomOut();
	tilemap.zoomOut();
        
        document.getElementById("demo").addEventListener("mousewheel", onWheelZoom);
        requestAnimationFrame(animate);
    }
    
    //main animation loop, updates tethers/URL/nodes, and repositions "top" elements each iteration
    function animate() {
        
        if (started) {
            physicsEngine.stepSimulation(1/60); // step simulation by 1/60th of a second
            var updates = physicsEngine.provideCoordinates();
            receiveCoordinates(updates);
        }
        requestAnimationFrame(animate);
        updateTethers();
        
        renderer.render(stage);
        
	//new tethers are redrawn every animation loop to correspond to updated location of the nodes
        function updateTethers() {
            tilemap.removeChild(graphics);
            graphics.clear();
            graphics.lineStyle(10, 0xffff33, 0.8);
            graphicsMap.forEach(function (item, index) {
                if (typeof graphicsMap[index][2] != 'undefined' && graphicsMap[index][2] != null) {
                    var startX = item[0]['position']['x'];
                    var startY = item[0]['position']['y'];
                    graphics.moveTo(startX, startY);
                    var endX = graphicsMap[item[2]][0]['position']['x'];
                    var endY = graphicsMap[item[2]][0]['position']['y'];
                    graphics.lineTo(endX, endY);
                }
            });
            graphics.endFill();
            tilemap.addChild(graphics);
            
	    //nodes are removed and then replaced to be on top of tethers as pixijs uses a linked list with
	    //sprite priority going to last on list
            graphicsMap.forEach(function (item, index) {
                tilemap.removeChild(item[0]);
                tilemap.addChild(item[0]);
            });


            if (popupText.height != 20/tilemap.zoom * 1.2) {
               popupText.height = 20/tilemap.zoom * 1.2; 
               popupText.scale.x = popupText.scale.y;
	    }

	    //to have the URL follow the sprite it is attached to, this occurs
	    if (popupText && currentSprite) {
               popupText.position.x = currentSprite.position.x + 40;
	       popupText.position.y = currentSprite.position.y - 10;  
	    }
	    tilemap.addChild(popupText);
        }
    }
}

//callback that occurs when a node is moused over
function onMouseover(event) {
    
    //currentSprite is set as global, and the node is matched to the graphics map
    currentSprite = event['target'];
    graphicsMap.forEach(function (item, index) {
        if (item[0] === currentSprite) {
            currentUrl = item[1];
        }
    });
   
    //a new URL pops up slightly offset from the location of the node it was spawned from 
    tilemap.removeChild(popupText);
    popupText = null;
    popupText = new PIXI.Text(currentUrl, { font: '36px Arial', fill: 0xff1010, dropShadow: true, dropShadowColor: 0x000000, dropShadowDistance: 3, align: 'center' });
    popupText.on('mousedown', takeHyperlink);
    popupText.interactive = true;
    popupText.buttonMode = true;
    popupText.height = 120/tilemap.zoom * 1.2; 
    popupText.scale.x = popupText.scale.y;

    popupText.position.x = event['target']['position']['x'] + 20;
    popupText.position.y = event['target']['position']['y'] - 10;
    tilemap.addChild(popupText);
}

//callback that occurs on node drag start 
function onDragStart(event) {
    tilemap.removeChild(popupText);
    //prevent the map beneath from simultanious drag, and turn off physics control of node
    turnParentDragOff();
    physicsEngine.nodeDragStart(event['target'].children[0].text);
    this.data = event.data;
    this.alpha = 0.5;
    this.dragging = true;
}

//callback that occurs on node drag end
function onDragEnd(event) {
    //return ability to both drag the canvas as well as physics control of the node
    turnParentDragOn();
    physicsEngine.nodeDragEnd(event['target'].children[0].text);
    this.alpha = 1;
    this.dragging = false;
    this.data = null;
}

//on drag move event
function onDragMove(event) {
    
   //if the node is actively being dragged
   if (this.dragging) {
        //update position based on the position provided by the event
        var newPosition = this.data.getLocalPosition(this.parent);
        this.position.x = newPosition.x;
        this.position.y = newPosition.y;
	//inform the physics engine and related popup text of the new position
        physicsEngine.updateNodeCoordinates(event['target'].children[0].text, this.position.x, this.position.y);
        popupText.position.x = newPosition.x + 20;
        popupText.position.y = newPosition.y - 10;
    }
}

//these functions allow node dragging without dragging map underneath
function turnParentDragOff() {
    tilemap.setChildDragging(true);
}
function turnParentDragOn() {
    tilemap.setChildDragging(false);
}

//On zoom event checks if the mousewheel was up or down and calls the tilemaps zoom in or out respectively
function onWheelZoom(event) {
    if (event.deltaY < 0) {
        tilemap.zoomIn();
    } else {
        tilemap.zoomOut();
    }
}

//Function used to provide mock "hyperlink" ability to a pixi.js sprite
function takeHyperlink(event) {
    window.open(currentUrl);
}

