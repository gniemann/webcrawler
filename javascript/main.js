var ySize;
var xSize;

window.onload = function () {
    
    var offset = $('#demo').offset();
    ySize = $(window).height() - offset.top - 30;
    xSize = $(window).width() - 80;
    
    graphicsEngine = new Main('', xSize, ySize);
    $('#demo').append(graphicsEngine);
    document.getElementsByTagName("html")[0].style.visibility = "visibile";
}

var physicsEngine = new SimulationRefactorInterface();
physicsEngine.setDisplayScale(18400, 16000, 15);

// define a few globals here
var graphicsEngine;
var renderer = null;
var renderWidth = 800;
var renderHeight = 600;

var tilemap = null;

var currentParentId = null;
var graphics = new PIXI.Graphics();
var popupText = new PIXI.Text('', { font: '36px Arial', fill: 0xff1010, align: 'center' });
popupText.on('mousedown', takeHyperlink);
popupText.interactive = true;
popupText.buttonMode = true;

var currentUrl;
var currentSprite;

var graphicsMap = [];

function switchType(value) {
    if (value == 'BFS') {
        $('#search_type').html('Search depth:');
    } else {
        $('#search_type').html('Max results:');
    }
}

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

function addNode(x, y, url, id, parentId) {
    
    var texture = PIXI.Texture.fromImage("images/sunburst.png");
    
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

function Main(tilesPath, w, h) {
    
    PIXI.scaleModes.DEFAULT = PIXI.scaleModes.NEAREST;
    stage = new PIXI.Stage(0x888888);
    if (w != 0 && h != 0) {
        renderWidth = w;
        renderHeight = h;
    }
    renderer = PIXI.autoDetectRenderer(renderWidth, renderHeight);
    
    var tileAtlas = [tilesPath + "tiles.json"];
    var loader = PIXI.loader;
    loader.add(tileAtlas);
    loader.once('complete', onLoaded);
    loader.load();
    
    return renderer.view;
    
    function onLoaded() {
        
        tilemap = new Tilemap(251, 251);
        stage.addChild(tilemap);
        
        // zoom in on the starting tile
        tilemap.selectTile(tilemap.startLocation.x, tilemap.startLocation.y);
        tilemap.zoomOut();
        
        document.getElementById("demo").addEventListener("mousewheel", onWheelZoom);
        requestAnimationFrame(animate);
    }
    
    function animate() {
        
        if (started) {
            var updates = physicsEngine.provideCoordinates();
            receiveCoordinates(updates);
        }
        requestAnimationFrame(animate);
        updateTethers();
        
        renderer.render(stage);
        
        function updateTethers() {
            tilemap.removeChild(graphics);
            graphics.clear();
            graphics.lineStyle(4, 0xffff33, 0.6);
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
            
            graphicsMap.forEach(function (item, index) {
                tilemap.removeChild(item[0]);
                tilemap.addChild(item[0]);
            });
	    if (popupText && currentSprite) {
               popupText.position.x = currentSprite.position.x + 20;
	       popupText.position.y = currentSprite.position.y - 10;  
	    }
	    tilemap.addChild(popupText);
        }
    }
}

function onMouseover(event) {
    currentSprite = event['target'];
    graphicsMap.forEach(function (item, index) {
        if (item[0] === currentSprite) {
            currentUrl = item[1];
        }
    });
    
    tilemap.removeChild(popupText);
    
    popupText = null;
    popupText = new PIXI.Text(currentUrl, { font: '36px Arial', fill: 0xff1010, align: 'center' });
    popupText.on('mousedown', takeHyperlink);
    popupText.interactive = true;
    popupText.buttonMode = true;
    popupText.position.x = event['target']['position']['x'] + 20;
    popupText.position.y = event['target']['position']['y'] - 10;
    tilemap.addChild(popupText);
}

function onDragStart(event) {
    tilemap.removeChild(popupText);
    turnParentDragOff();
    physicsEngine.nodeDragStart(event['target'].children[0].text);
    this.data = event.data;
    this.alpha = 0.5;
    this.dragging = true;
}

function onDragEnd(event) {
    turnParentDragOn();
    physicsEngine.nodeDragEnd(event['target'].children[0].text);
    this.alpha = 1;
    this.dragging = false;
    this.data = null;
}

function onDragMove(event) {
    
   if (this.dragging) {
        var newPosition = this.data.getLocalPosition(this.parent);
        this.position.x = newPosition.x;
        this.position.y = newPosition.y;
        physicsEngine.updateNodeCoordinates(event['target'].children[0].text, this.position.x, this.position.y);
        popupText.position.x = newPosition.x + 20;
        popupText.position.y = newPosition.y - 10;
    }
}

function turnParentDragOff() {
    tilemap.setChildDragging(true);
}

function turnParentDragOn() {
    tilemap.setChildDragging(false);
}

function onWheelZoom(event) {
    if (event.deltaY < 0) {
        tilemap.zoomIn();
    } else {
        tilemap.zoomOut();
    }
}

function takeHyperlink(event) {
    window.location = currentUrl;
}

