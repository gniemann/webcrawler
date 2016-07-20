var LinearScale = function () {
    var inputnear = 0.0;
    var inputfar = 1.0;
    var slope_toinput;
    var offset_toinput;
    var outputnear = 0.0;
    var outputfar = 1.0;
    var slope_tooutput;
    var offset_tooutput;
    
    this.setInputRange = function (near, far) {
        if (near == far) return;
        inputnear = near;
        inputfar = far;
        this.calculate();
    }
    
    this.setOutputRange = function (near, far) {
        if (near == far) return;
        outputnear = near;
        outputfar = far;
        this.calculate();
    }
    
    this.setRange = function (inputNear, inputFar, outputNear, outputFar) {
        if (inputNear == inputFar || outputNear == outputFar) return;
        inputnear = inputNear;
        inputfar = inputFar;
        outputnear = outputNear;
        outputfar = outputFar;
        this.calculate();
    }
    
    this.getInputNear = function () { return inputnear; }
    this.setInputNear = function (value) {
        if (value == inputnear) return;
        if (value == inputfar) inputfar = inputnear;
        inputnear = value;
        this.calculate();
    };
    this.getInputFar = function () { return inputfar; }
    this.setInputFar = function (value) {
        if (value == inputfar) return;
        if (value == inputnear) inputnear = inputfar;
        inputfar = value;
        this.calculate();
    };
    this.getInputRange = function () { return inputfar - inputnear; }
    
    this.getOutputFar = function () { return outputfar; }
    this.setOutputFar = function (value) {
        if (value == outputfar) return;
        if (value == outputnear) outputnear = outputfar;
        outputfar = value;
        this.calculate();
    };
    this.getOutputRange = function () { return outputfar - outputnear; }
    
    this.calculate = function () {
        slope_tooutput = (outputfar - outputnear) / (inputfar - inputnear);
        offset_tooutput = outputnear - slope_tooutput * inputnear;
        slope_toinput = (inputfar - inputnear) / (outputfar - outputnear);
        offset_toinput = inputnear - slope_toinput * outputnear;
    }
    
    this.toOutputScaleOffset = function (input) { return input * slope_tooutput + offset_tooutput; }
    this.toOutputScale = function (input) { return input * slope_tooutput; }
    this.toInputScaleOffset = function (output) { return output * slope_toinput + offset_toinput; }
    this.toInputScale = function (output) { return output * slope_toinput; }
    
    this.calculate();
};