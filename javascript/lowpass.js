// Simple lowpass filter for smoothing.
// http://en.wikipedia.org/wiki/Low-pass_filter
var Lowpass = function (alpha) {
    this.firstrun = true;
    this.y;
    this.alpha = alpha;
    
    /// <summary>
    /// Calculate alpha filter parameter from sample interval and cutoff frequency.
    /// </summary>
    /// <param name="dt">Sample interval (in seconds)</param>
    /// <param name="fc">Cutoff frequency</param>
    /// <returns>Alpha parameter.</returns>
    this.calculateAlpha = function (dt, fc) {
        return dt / ((1.0 / fc) + dt);
    }
    
    /// <summary>
    /// Apply filter to an input sample.
    /// </summary>
    /// <param name="x"></param>
    /// <returns>Current filtered output value.</returns>
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