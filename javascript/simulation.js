var Particle = function (id, params) {
    
    // id field, from the server
    this.id = id;
    
    this.fixity = false; // "permanently" fixed particle anchor
    if (params.hasOwnProperty('fixity')) this.fixity = (params.fixity ? true : false); // coerce to boolean
    
    this.hold = false; // "temporarily" fixed particle, e.g. for moving via UI
    
    // particle physics parameters
    this.mass = Number(params.mass);
    if (!isFinite(this.mass) || this.mass <= 0) this.mass = 1;
    
    this.charge = Number(params.charge);
    if (!isFinite(this.charge)) this.charge = 0;
    
    this.xf = new Lowpass(1);
    this.yf = new Lowpass(1);
    
    // updated as needed, see the updateParticle and updateAllParticles methods    
    // simulation values used for calculation are actually stored in the y and dydt solution vectors.
    this.x = Number(params.x);
    if (!isFinite(this.x)) this.x = 0;
    this.xf.y = this.x;
    
    this.y = Number(params.y);
    if (!isFinite(this.y)) this.y = 0;
    this.yf.y = this.y;
    
    // pixel positions
    this.px = 0;
    this.py = 0;
    
    // velocity
    this.vx = 0;
    this.vy = 0;
    
    // acceleration
    this.ax = 0;
    this.ay = 0;
    
    // force
    this.fx = 0;
    this.fy = 0;
    
    // array of Spring objects, containing the indices of the children of this particle
    this.children = [];
    
    this.applyForce = function (fx, fy) {
        this.fx += fx;
        this.fy += fy;
    }
    
    this.updateAcceleration = function (dt) {
        if (this.mass > 0) {
            
            //// log of the applied force magnitude
            //var f2 = this.fx * this.fx + this.fy * this.fy;
            //var f = Math.sqrt(f2);
            //if (f > 0) {
            //    //var logf = Math.abs(Math.log(f));
            //    var logf = Math.log(f);
            //    this.fx = logf * this.fx / f;
            //    this.fy = logf * this.fy / f;
            //}
            
            // update acceleration
            //var mc = this.mass;
            //if (this.children.length > 0) mc *= this.children.length;
            this.ax += this.fx / this.mass;
            this.ay += this.fy / this.mass;
            
            // clamp acceleration
            var a2 = this.ax * this.ax + this.ay * this.ay;
            var a = Math.sqrt(a2);
            
            if (a > 100) {
                this.ax = this.ax / a * 10;
                this.ay = this.ay / a * 10;
            }
            
            //// update velocity
            //var v1x = this.vx + this.ax * dt;
            //var v1y = this.vy + this.ay * dt;
            //var v12 = v1x * v1x + v1y * v1y;
            //var v1 = Math.sqrt(v12);
            
            //var v02 = this.vx * this.vx + this.vy * this.vy;
            //v0 = Math.sqrt(v02);
            
            //if (v1 < v0) {
            //    this.vx = v1x;
            //    this.vy = v1y;
            //}
            //else {
            //    this.vx = this.ax * dt * 0.5;
            //    this.vy = this.ay * dt * 0.5;
            //}
            
            this.vx += this.ax * dt;
            this.vy += this.ay * dt;
            
            //var v2 = this.vx * this.vx + this.vy * this.vy;
            //var v = Math.sqrt(v2);
            
            //if (v > 2) {
            //    this.vx = this.vx / v * 10;
            //    this.vy = this.vy / v * 10;
            //}
            
            // update displacement
            this.x += this.vx * dt;
            this.y += this.vy * dt;
            
            this.xf.alpha = 1 / Math.pow(this.children.length + 1, 1);
            this.yf.alpha = 1 / Math.pow(this.children.length + 1, 1);
            
            this.x = this.xf.update(this.x + this.vx * dt);
            this.y = this.yf.update(this.y + this.vy * dt);

        }
    };
};


var Spring = function (params) {
    this.restLength = params.restLength;
    this.springConstant = params.springConstant;
    this.dampingRatio = params.dampingRatio;
    
    this.childIndex = params.childIndex;
};

var Simulation = function () {
    
    this.xmin = -6;
    this.xmax = 6;
    this.ymin = -6;
    this.ymax = 6;
    //this.rmax = 500;
    this.t = 0;
    this.particles = [];
    var rmin = 0.05; //avoid singularity if particles align directly on top of each other
    var like_attract = false; //true if like signed charges attract (gravitational behavior), false if the repel (electrical behavior)
    
    // get the position of a particle
    // the index refers to the index in particles[] array, NOT to the particle ID
    // x and y are in the physical simulation scale
    this.getParticlePosition = function (index) {
        return {
            x: this.particles[index].x,
            y: this.particles[index].y,
        };
    };
    
    this.updateParticle = function (index) {
        return this.particles[index];
    };
    
    this.updateAllParticles = function () {
        return this.particles;
    };
    
    // set the position of a particle
    // the index refers to the index in particles[] array, NOT to the particle ID
    // x and y are in the physical simulation scale
    this.setParticlePosition = function (index, x, y) {
        this.particles[index].x = x;
        this.particles[index].xf.y = x;
        this.particles[index].y = y;
        this.particles[index].yf.y = y;
    };
    
    this.setEachParticle = function (property, value) {
        for (var i = 0; i < this.particles.length; i++) {
            this.particles[i][String(property)] = value;
        }
    };
    
    this.setEachSpring = function (property, value) {
        var particle;
        var spring;
        for (var i = 0; i < this.particles.length; i++) {
            particle = this.particles[i];
            for (var j = 0; j < particle.children.length; j++) {
                spring = particle.children[j];
                spring[String(property)] = value;
            }
        }
    };
    
    // apply the specified timestep to the force model
    this.step = function (dt) {
        
        var particle;
        this.t += dt;
        
        // reset acceleration
        for (var i = 0; i < this.particles.length; i++) {
            
            particle = this.particles[i];
            // reset force
            particle.fx = 0;
            particle.fy = 0;
            
            // reset acceleration
            particle.ax = 0;
            particle.ay = 0;
            
            // particle fixed in place, e.g. under user control
            if (particle.fixity || particle.hold) {
                // no velocity
                particle.vx = 0;
                particle.vy = 0;
            }
        }
        
        // evaluate physics for each particle and spring
        for (var i = 0; i < this.particles.length; i++) {
            evaluateCharge(this.particles, i);
            evaluateSprings(this.particles, i);
        }
        
        // apply accelerations
        for (var i = 0; i < this.particles.length; i++) {
            if (!this.particles[i].hold && !this.particles[i].fixity) {
                this.particles[i].updateAcceleration(dt);
            }
            else {
                this.particles[i].xf.y = this.particles[i].x;
                this.particles[i].yf.y = this.particles[i].y;
            }
        }
        
        //// constrain children to be within radius of their parents
        //var parent, child;
        //var dx, dy;
        //var r2, r;
        //for (var i = 0; i < this.particles.length; i++) {
        //    parent = this.particles[i];
        //    for (var j = 0; j < parent.children.length; j++) {
        //        child = this.particles[parent.children[j].childIndex];
        //        dx = child.x - parent.x;
        //        dy = child.y - parent.y;
        //        r2 = dx * dx + dy * dy;
        //        r = Math.sqrt(r2);
        //        if (r > this.rmax) {
        //            child.vx = 0;
        //            child.vy = 0;
        //            child.x = parent.x + dx / r * this.rmax;
        //            child.y = parent.y + dy / r * this.rmax;
        //        }
        //    };
        //};
        
        //// constrain children to be within radius of the root
        //var dx, dy;
        //var r2, r;
        //root = this.particles[0];
        //for (var i = 0; i < this.particles.length; i++) {
        //    particle = this.particles[i];
        //    dx = particle.x - root.x;
        //    dy = particle.y - root.y;
        //    r2 = dx * dx + dy * dy;
        //    r = Math.sqrt(r2);
        //    if (r > this.rmax) {
        //        particle.vx = 0;
        //        particle.vy = 0;
        //        particle.x = root.x + dx / r * this.rmax;
        //        particle.y = root.y + dy / r * this.rmax;
        //    }
        //};
        
        //// constrain children to be within radius of the root, reflect them back (sort of)
        //var dx, dy;
        //var r2, r;
        //var v2, v;
        //var rr;
        //root = this.particles[0];
        //for (var i = 0; i < this.particles.length; i++) {
        //    particle = this.particles[i];
        //    dx = particle.x - root.x;
        //    dy = particle.y - root.y;
        //    r2 = dx * dx + dy * dy;
        //    r = Math.sqrt(r2);
        //    if (r > this.rmax) {
        //        rr = r - this.rmax;
        //        particle.vx = -particle.vx;
        //        particle.vy = -particle.vy;
        
        //        particle.x = root.x + dx / r * this.rmax;
        //        particle.y = root.y + dy / r * this.rmax;
        
        //        v2 = particle.vx * particle.vx + particle.vy * particle.vy;
        //        v = Math.sqrt(v2);
        //        particle.x += rr * particle.vx / v;
        //        particle.y += rr * particle.vy / v;
        //    }
        //};
        
        //// constrain children to be within radius of the root, with filter
        //var dx, dy;
        //var r2, r;
        //root = this.particles[0];
        //for (var i = 0; i < this.particles.length; i++) {
        //    particle = this.particles[i];
        //    dx = particle.x - root.x;
        //    dy = particle.y - root.y;
        //    r2 = dx * dx + dy * dy;
        //    r = Math.sqrt(r2);
        //    if (r > this.rmax) {
        //        particle.vx = 0;
        //        particle.vy = 0;
        //        particle.x = root.x + dx / r * this.rmax;
        //        particle.y = root.y + dy / r * this.rmax;
        //        particle.xf.y = particle.x;
        //        particle.yf.y = particle.y;
        //    }
        //};
        
        // constrain children to be within radius of the root, with filter
        for (var i = 0; i < this.particles.length; i++) {
            particle = this.particles[i];
            
            if (particle.x < this.xmin) {
                particle.x = this.xmin;
                particle.xf.y = particle.x;
            }
            else if (particle.x > this.xmax) {
                particle.x = this.xmax;
                particle.xf.y = particle.x;
            }
            
            if (particle.y < this.ymin) {
                particle.y = this.ymin;
                particle.yf.y = particle.y;
            }
            else if (particle.y > this.ymax) {
                particle.y = this.ymax;
                particle.yf.y = particle.y;
            }
        };

    };
    
    var evaluateSprings = function (particles, index) {
        var dx, dy;
        var r2, r;
        var cos, sin;
        var theta;
        var f;
        var s;
        var c;
        var parent;
        var spring;
        var child;
        
        parent = particles[index];
        
        for (var i = 0; i < parent.children.length; i++) {
            spring = parent.children[i];
            if (index == spring.childIndex) continue; //ignore particles connected to themselves
            child = particles[spring.childIndex];
            
            // distance between particles
            dx = parent.x - child.x;
            dy = parent.y - child.y;
            r2 = dx * dx + dy * dy;
            r = Math.sqrt(r2); //distance between particles
            if (r > 0.0) {
                // calculate component trig ratio components
                cos = dx / r;
                sin = dy / r;
            }
            else {
                //calculate the force components using a random angle
                theta = 2.0 * Math.PI * Math.random();
                cos = Math.cos(theta);
                sin = Math.sin(theta);
            }
            
            // spring strain (stretched length)
            s = r - spring.restLength;
            
            //parent is free...
            if (!parent.hold && !parent.fixity) {
                f = -spring.springConstant * s;
                parent.applyForce(f * cos, f * sin);
                
                // calculate damping from damping ratio
                // zeta = b / (2 * sqrt(m*k)) --> b = 2 * sqrt(m*k) / zeta
                // calculate critical damping...
                c = 2.0 * Math.sqrt(parent.mass * spring.springConstant);
                c *= spring.dampingRatio; // ...then adjust for damping ratio
                parent.applyForce(-c * parent.vx, -c * parent.vy);
            }
            
            //child is free...
            if (!child.hold && !child.fixity) {
                //force has opposite sign for p2
                f = spring.springConstant * s;
                child.applyForce(f * cos, f * sin);
                
                // calculate damping from damping ratio
                // zeta = b / (2 * sqrt(m*k)) --> b = 2 * sqrt(m*k) / zeta
                // critical damping
                c = 2.0 * Math.sqrt(child.mass * spring.springConstant);
                c *= spring.dampingRatio; // ...then adjust for damping ratio
                child.applyForce(-c * child.vx, -c * child.vy);
            }
        }
    }
    
    // evaluate the charge physics for a particle
    // modified to calculate charge force contributions ONLY from child nodes
    // on other child nodes
    var evaluateChargeChildren = function (particles, index) {
        var dx, dy;
        var r2, r;
        var cos, sin;
        var theta;
        var f;
        var parent, pi, pj, si, sj;
        var pix, piy;
        var ci, cj;
        
        parent = particles[index];
        
        for (var i = 0; i < parent.children.length; i++) {
            si = parent.children[i];
            pi = particles[si.childIndex];
            if (!pi.hold && !pi.fixity && pi.mass > 0) {
                pix = pi.x; // y[si.childIndex * EQS + Y_X];
                piy = pi.y; // y[si.childIndex * EQS + Y_Y];
                for (var j = 0; j < parent.children.length; j++) {
                    if (i == j) continue;
                    sj = parent.children[j];
                    pj = particles[sj.childIndex];
                    //if (!pj.hold && !pj.fixity && pj.mass > 0) {
                    
                    dx = pix - pj.x; // y[sj.childIndex * EQS + Y_X];
                    dy = piy - pj.y; // y[sj.childIndex * EQS + Y_Y];
                    
                    r2 = dx * dx + dy * dy; //distance^2 between particles
                    
                    r = Math.sqrt(r2); //distance between particles
                    if (r > 0.0) {
                        cos = dx / r;
                        sin = dy / r;
                    }
                    else {
                        //avoid angular singularity; use a random angle
                        theta = 2.0 * Math.PI * Math.random();
                        cos = Math.cos(theta);
                        sin = Math.sin(theta);
                    }
                    if (r < rmin) r2 = rmin * rmin; //limit the minimum distance between particles (hence the maximum force)
                    
                    // include charges of children
                    ci = pi.charge;
                    if (pi.children.length > 0) ci *= Math.pow(pi.children.length, 0.8);
                    
                    cj = pj.charge;
                    if (pj.children.length > 0) cj *= Math.pow(pj.children.length, 0.8);
                    
                    //f = pi.charge * pj.charge / r2;
                    f = ci * cj / r2;
                    if (like_attract) f = -f;
                    
                    // apply force
                    pi.applyForce(f * cos, f * sin);
                    //dydt[si.childIndex * EQS + DYDT_AX] += (f * cos) / pi.mass;
                    //dydt[si.childIndex * EQS + DYDT_AY] += (f * sin) / pi.mass;
                    //}
                }
            }
        }
    };
    
    var evaluateCharge = function (particles, index) {
        var dx, dy;
        var r2, r;
        var cos, sin;
        var theta;
        var f;
        var particle, other;
        
        particle = particles[index];
        if (particle.hold || particle.fixity) return;
        
        //accelerations due to charges from (all) other particles
        for (var i = 0; i < particles.length; i++) {
            if (index == i) continue; //don't evaluate a particle against itself
            other = particles[i];
            dx = particle.x - other.x; //positive when index to the right of i
            dy = particle.y - other.y; //positive when index above i
            
            r2 = dx * dx + dy * dy; //distance^2 between particles
            
            r = Math.sqrt(r2); //distance between particles
            if (r > 0.0) {
                cos = dx / r;
                sin = dy / r;
            }
            else {
                //avoid angular singularity; use a random angle
                theta = 2.0 * Math.PI * Math.random();
                cos = Math.cos(theta);
                sin = Math.sin(theta);
            }
            if (r < rmin) r2 = rmin * rmin; //limit the minimum distance between particles (hence the maximum force)
            
            f = particles[index].charge * particles[i].charge / r2;
            if (like_attract) f = -f;
            
            particles[index].applyForce(f * cos, f * sin);
        }
    };
    
    
    // get the bounding box for all the particle (centers)
    this.getParticleBounds = function () {
        bounds = { w: 0, h: 0 };
        for (var i = 0; i < this.particles.length; i++) {
            var p = this.getParticlePosition(index);
            if (bounds.x === undefined || p.x < bounds.x) bounds.x = p.x;
            if (bounds.y === undefined || p.y < bounds.y) bounds.y = p.y;
            var w = p.x - bounds.x;
            if (w > bounds.w) bounds.w = w;
            var h = p.y - bounds.y;
            if (h > bounds.h) bounds.h = h;
        }
        return bounds;
    };
    
    
    this.clear = function () {
        this.particles = [];
    };
    
    // add a particle
    // with the specified parent, position, and spring characteristics
    this.addParticle = function (p, parent, springRestLength, springConstant, springDampingRatio) {
        var index = this.particles.length;
        if (parent >= 0) {
            this.particles[parent].children.push(new Spring(
                {
                    childIndex: this.particles.length,
                    restLength: springRestLength,
                    springConstant: springConstant,
                    dampingRatio: springDampingRatio
                }));
        }
        
        // preserve state
        this.particles.push(p);
        return index;
    };
};