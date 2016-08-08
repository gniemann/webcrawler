// Filename: lowpass.js
// Author: Jason Loomis
// Date: July 17, 2016
//
// Description: Provides an implementation of a simple infinite-impulse-response
// (IIR) lowpass filter with a user-specifiable alpha (normalized frequency
// response). Use for smoothing a signal with undesired high-frequency content.
//
// Dependencies: none
//
// Usage: create a Lowpass object and specify the alpha (frequency response)
// value. For a discrete time series signal with a regular sampling rate, the
// Lowpass.calculateAlpha method may be used to determine an alpha value for
// a desired cutoff frequency
//
// Code is based on the article found here:
// http://en.wikipedia.org/wiki/Low-pass_filter


// provides a representation of a simple IIR lowpass filter.
// Note: to re-initialize the filter, set "firstrun" to a value that evaluates
// to true.
var Lowpass = function (alpha) {
    this.firstrun = true;
    this.y;
    this.alpha = alpha;
    
    // Calculate alpha filter parameter from sample interval and cutoff frequency.
    // dt: Sample interval (in seconds)
    // fc: Cutoff frequency (in Hz)
    // returns: normalized frequency cutoff alpha parameter
    this.calculateAlpha = function (dt, fc) {
        return dt / ((1.0 / fc) + dt);
    }
    
    // apply filter to an input sample.
    // x: an input value
    // returns: the current filtered output value
    this.update = function(x)
    {
        if (this.firstrun) {
            this.y = x;
            this.firstrun = false;
        }
        else this.y = this.y + this.alpha * (x - this.y);
        return this.y;
    }
}