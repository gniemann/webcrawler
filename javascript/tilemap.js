Tilemap.prototype = new PIXI.DisplayObjectContainer();
Tilemap.prototype.constructor = Tilemap;

function Tilemap(width, height){
  PIXI.DisplayObjectContainer.call(this);
  this.interactive = true;

  this.tilesWidth = 92;
  this.tilesHeight = 80;
  this.childDragging = false;

  this.tileSize = 200;
  this.zoom = 1;
  this.scale.x = this.scale.y = this.zoom;

  this.startLocation = { x: 40, y: 40 };

  this.createGrid();

  // variables and functions for moving the map
  this.mouseoverTileCoords = [0, 0];
  this.selectedTileCoords = [0, 0];
  this.mousePressPoint = [0, 0];
  this.selectedGraphics = new PIXI.Graphics();
  this.mouseoverGraphics = new PIXI.Graphics();
  this.addChild(this.selectedGraphics);
  this.addChild(this.mouseoverGraphics);

  this.mousedown = this.touchstart = function(data) {
     if(!this.childDragging){   
	this.dragging = true;
	this.mousePressPoint[0] = data.data.getLocalPosition(this.parent).x - this.position.x;
	this.mousePressPoint[1] = data.data.getLocalPosition(this.parent).y - this.position.y;
	this.selectTile(Math.floor(this.mousePressPoint[0] / (this.tileSize * this.zoom)),
	      Math.floor(this.mousePressPoint[1] / (this.tileSize * this.zoom)));
     }
  };

  this.mouseup = this.mouseupoutside =
    this.touchend = this.touchendoutside = function(data) {
    this.dragging = false;
  };

  this.mousemove = this.touchmove = function(data)
  {
     if(!this.childDragging){
     	if(this.dragging)
	{
	   var position = data.data.getLocalPosition(this.parent);
	   this.position.x = position.x - this.mousePressPoint[0];
   	   this.position.y = position.y - this.mousePressPoint[1];
	   this.constrainTilemap();
	}
	this.mousePressPoint[0] = data.data.getLocalPosition(this.parent).x - this.position.x;
	this.mousePressPoint[1] = data.data.getLocalPosition(this.parent).y - this.position.y;
	this.selectTile(Math.floor(this.mousePressPoint[0] / (this.tileSize * this.zoom)),
	      Math.floor(this.mousePressPoint[1] / (this.tileSize * this.zoom)));
     }
  };
}

Tilemap.prototype.setChildDragging = function(childDragging){
   this.childDragging = childDragging;
}

Tilemap.prototype.addTile = function(x, y, terrain){
  
  var tile = PIXI.Sprite.fromImage("images/gridTile4.png"); 
  tile.position.x = x * this.tileSize;
  tile.position.y = y * this.tileSize;
  tile.tileX = x;
  tile.tileY = y;
  tile.terrain = terrain;
  this.addChildAt(tile, x * this.tilesHeight + y);
}

Tilemap.prototype.getTile = function(x, y){
  return this.getChildAt(x * this.tilesHeight + y);
}

Tilemap.prototype.createGrid = function(){

  for(var i = 0; i < this.tilesWidth; i++){
    for(var j = 0; j < this.tilesHeight; j++){
       this.addTile(i, j, 1);
    }
  }
}

Tilemap.prototype.selectTile = function(x, y){
  this.selectedTileCoords = [x, y];
}

Tilemap.prototype.zoomIn = function(){
   
   if (this.zoom != 1){
      this.zoom = Math.min(this.zoom * 2, 1);
     
      popupText.font = 20/this.zoom;
      this.removeChild(popupText);
      this.addChild(popupText);
      
      this.scale.x = this.scale.y = this.zoom;
      this.centerOnSelectedTile();
      this.constrainTilemap();
   }
}

Tilemap.prototype.zoomOut = function(){

   if (this.zoom != 0.1){
      
      this.mouseoverGraphics.clear();
      this.zoom = Math.max(this.zoom / 2, 0.1);
      
      popupText.font = 20/this.zoom;
      this.removeChild(popupText);
      this.addChild(popupText);
      
      this.scale.x = this.scale.y = this.zoom;
      this.centerOnSelectedTile();
      this.constrainTilemap();
   }
}

Tilemap.prototype.centerOnSelectedTile = function(){
  
   this.position.x = renderWidth / 2 - this.selectedTileCoords[0] * this.zoom * this.tileSize -
   this.tileSize * this.zoom / 2;
   
   this.position.y = renderHeight / 2 - this.selectedTileCoords[1] * this.zoom * this.tileSize -
   this.tileSize * this.zoom / 2;
}

Tilemap.prototype.constrainTilemap = function(){
  
   this.position.x = Math.max(this.position.x, -1 * this.tileSize * this.tilesWidth * this.zoom + renderWidth);
  this.position.x = Math.min(this.position.x, 0);
  
  this.position.y = Math.max(this.position.y, -1 * this.tileSize * this.tilesHeight * this.zoom + renderHeight);
  this.position.y = Math.min(this.position.y, 0);
}
