/*
 * Tilemap.js is originally work of: www.bhopkins.net/2014/10/08/draggable-zoomable-tile-map-with-pixi-js/. 
 * It was heavily modified from the original version for use in this project. Major modifications include
 * updating it to be compliant with latest version of PIXI.js, changing mouse zooming to be at mouse location.
 * The zoom functionality no longer relies on having to select a tile and then click + or - in menu, and can
 * be done dynamically with the mouse wheel now. Other adjusted highlighted below
 *
 * Original Author: bhopkins
 * Refactoed Author: Ashton Herrington
 * Last modified Date: 08/01/16 
 */

//extend DisplayObjectContainer
Tilemap.prototype = new PIXI.DisplayObjectContainer();
Tilemap.prototype.constructor = Tilemap;

//Define the tilemap
function Tilemap(width, height){
  PIXI.DisplayObjectContainer.call(this);
  this.interactive = true;
  
  //currently set to 160 tiles wide by 80 tiles high, may change as the BFS options become larger
  this.tilesWidth = 160;
  this.tilesHeight = 80;
  //by default you can drag the map since a child is not being dragged
  this.childDragging = false;

  //tiles are 200 pixels by 200 pixels, specifically tied to the .png file associated with tile creation
  this.tileSize = 200;
  this.zoom = 1;
  this.scale.x = this.scale.y = this.zoom;

  //this is the tile that the viewer starts on
  this.startLocation = { x: 80, y: 40 };
  this.createGrid();

  // variables and functions for moving the map
  this.mouseoverTileCoords = [0, 0];
  this.selectedTileCoords = [0, 0];
  this.mousePressPoint = [0, 0];
  this.selectedGraphics = new PIXI.Graphics();
  this.mouseoverGraphics = new PIXI.Graphics();
  this.addChild(this.selectedGraphics);
  this.addChild(this.mouseoverGraphics);

  //begin dragging the map on mousedown
  this.mousedown = this.touchstart = function(data) {
     //only allow repositioning of map if a child node is not being dragged
     if(!this.childDragging){   
	this.dragging = true;
	this.mousePressPoint[0] = data.data.getLocalPosition(this.parent).x - this.position.x;
	this.mousePressPoint[1] = data.data.getLocalPosition(this.parent).y - this.position.y;
	this.selectTile(Math.floor(this.mousePressPoint[0] / (this.tileSize * this.zoom)),
	      Math.floor(this.mousePressPoint[1] / (this.tileSize * this.zoom)));
     }
  };

  //end dragging th map on mouseup
  this.mouseup = this.mouseupoutside =
    this.touchend = this.touchendoutside = function(data) {
    this.dragging = false;
  };

  //on mouse move event
  this.mousemove = this.touchmove = function(data)
  {
     //if the child is not being dragged, and the map is
     if(!this.childDragging){
     	if(this.dragging)
	{
	   //get the position from the data and set to new position
	   var position = data.data.getLocalPosition(this.parent);
	   this.position.x = position.x - this.mousePressPoint[0];
   	   this.position.y = position.y - this.mousePressPoint[1];
	   this.constrainTilemap();
	}
	//select the tile at the new position
	this.mousePressPoint[0] = data.data.getLocalPosition(this.parent).x - this.position.x;
	this.mousePressPoint[1] = data.data.getLocalPosition(this.parent).y - this.position.y;
	this.selectTile(Math.floor(this.mousePressPoint[0] / (this.tileSize * this.zoom)),
	      Math.floor(this.mousePressPoint[1] / (this.tileSize * this.zoom)));
     }
  };
}

//New function, if a node is being dragged, set this to prevent map from being dragging alongside with it
Tilemap.prototype.setChildDragging = function(childDragging){
   this.childDragging = childDragging;
}


//adds pixi sprites to the grid, this creates the interactive background tiles
Tilemap.prototype.addTile = function(x, y, terrain){
  var tile = PIXI.Sprite.fromImage("images/gridTile4.png"); 
  tile.position.x = x * this.tileSize;
  tile.position.y = y * this.tileSize;
  tile.tileX = x;
  tile.tileY = y;
  tile.terrain = terrain;
  this.addChildAt(tile, x * this.tilesHeight + y);
}

//acquire tile that is highlighted
Tilemap.prototype.getTile = function(x, y){
  return this.getChildAt(x * this.tilesHeight + y);
}

//new createGrid function creates a static repeating grid instead of a randomly generated world
Tilemap.prototype.createGrid = function(){

  for(var i = 0; i < this.tilesWidth; i++){
    for(var j = 0; j < this.tilesHeight; j++){
       this.addTile(i, j, 1);
    }
  }
}

//tile selection, used for both dragging and zooming the map
Tilemap.prototype.selectTile = function(x, y){
  this.selectedTileCoords = [x, y];
}

//New zoom in functionality, allows user to zoom in at the point of the mouse
Tilemap.prototype.zoomIn = function(){
   
   //if at maximum zoom in already, do not readjust contents of the screen, do nothing
   if (this.zoom != 0.8){
      this.zoom = Math.min(this.zoom * 2, 0.8);
    
      //rescale the map, and recenter afterwards to esnure at a valid central tile
      this.scale.x = this.scale.y = this.zoom;
      this.centerOnSelectedTile();
      this.constrainTilemap();
   }
}

//New zoom out functionality, allows user to zoom out at the point of the mouse
Tilemap.prototype.zoomOut = function(){

   //if at maximum zoom already, do not readjust contents of the screen, do nothing
   if (this.zoom != 0.08){
      this.zoom = Math.max(this.zoom / 2, 0.08);
      
      //rescale the map, and recenter afterwards to ensure at a valid central tile
      this.scale.x = this.scale.y = this.zoom;
      this.centerOnSelectedTile();
      this.constrainTilemap();
   }
}

//Legacy code from existing tilemap, the key change here is that I have altered this to not allow for the addition
//of a menu bar, so the map is capable fo taking up the entire screen
Tilemap.prototype.centerOnSelectedTile = function(){
  
   this.position.x = renderWidth / 2 - this.selectedTileCoords[0] * this.zoom * this.tileSize -
   this.tileSize * this.zoom / 2;
   
   this.position.y = renderHeight / 2 - this.selectedTileCoords[1] * this.zoom * this.tileSize -
   this.tileSize * this.zoom / 2;
}


//Legacy code from the existing Tilemap, this prevents centering on a Tile that is too far to the edge of the
//map such that the field of view is always covered completely by the tile map.
Tilemap.prototype.constrainTilemap = function(){
  
  this.position.x = Math.max(this.position.x, -1 * this.tileSize * this.tilesWidth * this.zoom + renderWidth);
  this.position.x = Math.min(this.position.x, 0);
  
  this.position.y = Math.max(this.position.y, -1 * this.tileSize * this.tilesHeight * this.zoom + renderHeight);
  this.position.y = Math.min(this.position.y, 0);
}
