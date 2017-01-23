// Filename: linearScale.js
// Author: Jason Loomis
// Date: July 17, 2016
//
// Description: Manages a linear transformation between values in one scaling
// system (input scale) to another scaling system (output scale).
// Used to maintain the relationship between a physical scale (physical units)
// and a screen scale (pixels).
//
// Dependencies: none
//
// Usage: create a LinearScale object and set its input and output scales
// (using the set___ functions). These scales may be updated at any time using
// the same functions. Use the get___ functions to transform values from one
// scaling system to the other. Note that the terminology "near" and "far" used
// below may have any meaning that the user chooses in terms of the scaling
// system. For instance, an x-axis scale may use "near" to refer to the left end
// of the scale and "far" to refer to the right end of the scale.

var LinearScale = function () {
    var inputnear = 0.0;
    var inputfar = 1.0;
    var slope_toinput;
    var offset_toinput;
    var outputnear = 0.0;
    var outputfar = 1.0;
    var slope_tooutput;
    var offset_tooutput;
    
    // specify two points to set the input scale, a "near" and "far" point
    // note that these points are NOT the endpoints of the scale, i.e.
    // transformed values will not be clamped to be within the range [near, far]
    this.setInputRange = function (near, far) {
        if (near == far) return;
        inputnear = near;
        inputfar = far;
        this.calculate();
    }

    // specify two points to set the output scale, a "near" and "far" point
    // note that these points are NOT the endpoints of the scale, i.e.
    // transformed values will not be clamped to be within the range [near, far]
    this.setOutputRange = function (near, far) {
        if (near == far) return;
        outputnear = near;
        outputfar = far;
        this.calculate();
    }

    // specify two points to set the input scale and two points to set the
    // output scale, the "near" and "far" points for each.
    // note that these points are NOT the endpoints of the scale, i.e.
    // transformed values will not be clamped to be within the range [near, far]
    this.setRange = function (inputNear, inputFar, outputNear, outputFar) {
        if (inputNear == inputFar || outputNear == outputFar) return;
        inputnear = inputNear;
        inputfar = inputFar;
        outputnear = outputNear;
        outputfar = outputFar;
        this.calculate();
    }
    
    // return the input scale "near" value
    this.getInputNear = function () { return inputnear; }
    
    // set the input scale "near" value
    this.setInputNear = function (value) {
        if (value == inputnear) return;
        if (value == inputfar) inputfar = inputnear;
        inputnear = value;
        this.calculate();
    };
    
    // return the input scale "far" value
    this.getInputFar = function () { return inputfar; }
    
    // set the input scale "far" value
    this.setInputFar = function (value) {
        if (value == inputfar) return;
        if (value == inputnear) inputnear = inputfar;
        inputfar = value;
        this.calculate();
    };
    
    // get the difference between the input "far" and "near" values
    this.getInputRange = function () { return inputfar - inputnear; }
    
    // return the output scale "near" value
    this.getOutputNear = function () { return outputnear; }
    
    // set the output scale "near" value
    this.setOutputNear = function (value) {
        if (value == outputnear) return;
        if (value == outputfar) outputfar = outputnear;
        outputnear = value;
        this.calculate();
    };
    
    // get the output scale "far" value
    this.getOutputFar = function () { return outputfar; }
    
    // set the output scale "far" value
    this.setOutputFar = function (value) {
        if (value == outputfar) return;
        if (value == outputnear) outputnear = outputfar;
        outputfar = value;
        this.calculate();
    };
    
    // get the difference between the output "far" and "near" values
    this.getOutputRange = function () { return outputfar - outputnear; }
    
    // recalculate the scaling transformation values
    // note: this function is automatically called by all of the functions
    // that assign input or output values
    this.calculate = function () {
        slope_tooutput = (outputfar - outputnear) / (inputfar - inputnear);
        offset_tooutput = outputnear - slope_tooutput * inputnear;
        slope_toinput = (inputfar - inputnear) / (outputfar - outputnear);
        offset_toinput = inputnear - slope_toinput * outputnear;
    }
    
    // transform an absolute value in the input scale to the output scale
    this.toOutputScaleOffset = function (input) { return input * slope_tooutput + offset_tooutput; }
    
    // transform a relative value in the input scale to the output scale
    this.toOutputScale = function (input) { return input * slope_tooutput; }
    
    // transform an absolute value in the output scale to the input scale
    this.toInputScaleOffset = function (output) { return output * slope_toinput + offset_toinput; }
    
    // transform a relative value in the output scale to the input scale
    this.toInputScale = function (output) { return output * slope_toinput; }
    
    this.calculate();
};