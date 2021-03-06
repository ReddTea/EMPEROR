# @auto-fold regex /^\s*if/ /^\s*else/ /^\s*def/
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import scipy as sp
from PyAstronomy.pyasl import MarkleyKESolver
from emperors_library import normal_pdf
import batman
import copy

def RV_model(THETA, time, kplanets):
    modelo = 0.0
    #sp.seterr(all=='raise')
    if kplanets == 0:
        return 0.0
    for i in range(kplanets):
        P, As, Ac, S, C = THETA[5*i:5*(i+1)]
        #P, As, Ac, ecc, w = THETA[5*i:5*(i+1)]
        A = As ** 2 + Ac ** 2
        ecc = S ** 2 + C ** 2

        phase = sp.arccos(Ac / (A ** 0.5))
        w = sp.arccos(C / (ecc ** 0.5))  # longitude of periastron

        ### test
        if S < 0:
            w = 2 * sp.pi - sp.arccos(C / (ecc ** 0.5))
        if As < 0:
            phase = 2 * sp.pi - sp.arccos(Ac / (A ** 0.5))

        ###
        #  sp.seterr(all='raise') # DEL
        per = sp.exp(P)
        freq = 2. * sp.pi / per
        M = freq * time + phase  # mean anomaly
        E = sp.array([MarkleyKESolver().getE(m, ecc) for m in M])  # eccentric anomaly
        f = (sp.arctan(((1. + ecc) ** 0.5 / (1. - ecc) ** 0.5) * sp.tan(E / 2.)) * 2.)  # true anomaly
        modelo += A * (sp.cos(f + w) + ecc * sp.cos(w))
    return  modelo


def acc_model(theta, time, ACC):
    if ACC > 0:  # recheck this at some point # DEL
        y = sp.polyval(sp.r_[0, theta[:ACC]], (time-sp.amin(time)))
        return y
    else:
        return 0.


def inst_moav(theta, time, ins, nins, moav, residuals):
    """Calculate the instrumental moving average model."""
    counter = 0
    insmoav = sp.zeros_like(time)
    for i in range(nins):
        idx = ins == i
        time_ins = time[idx]
        for t in range(len(time_ins)):
            for c in range(moav[i]):
                th = theta[counter:counter + moav[i]*2]
                if t > c:
                    res = residuals[i - 1 - c]
                    dt = sp.fabs(time_ins[t - 1 - c] - time_ins[t])
                    coeff = th[c].val
                    timescale = th[c + 1].val
                    MA = coeff * sp.exp(-dt / timescale) * res
                    insmoav[i] = MA
        counter += moav[i] * 2
    return insmoav


def stellar_moav(theta, time, star_moav, residuals):
    """Calculate the stellar moving average model."""
    moav = sp.zeros_like(time)
    for i in range(len(time)):
        for c in range(star_moav):
            if i > c:
                dt = sp.fabs(time[i - 1 - c] - time[i])
                timescale = theta[2 * c + 1]
                MA = theta[2 * c] * sp.exp(-dt / timescale)
                MA *= residuals[i - 1 - c]
                moav[i] = MA
    return moav


def gen_model(theta, time, MOAV, residuals):
    """Stellar moving average.
    In goes residuals, and out too!
    """
    for i in range(len(time)):
        for c in range(MOAV):
            if i > c:
                MA = theta[2*c] * sp.exp(-sp.fabs(time[i-1-c] - time[i]) / theta[2*c + 1]) * residuals[i-1-c]
                residuals[i] -= MA
    return residuals


def mini_RV_model(params, time):
    P, A, phase, ecc, w = params
    freq = 2. * sp.pi / P
    M = freq * time + phase
    E = sp.array([MarkleyKESolver().getE(m, ecc) for m in M])
    f = (sp.arctan(((1. + ecc) ** 0.5 / (1. - ecc) ** 0.5) * sp.tan(E / 2.)) * 2.)
    modelo = A * (sp.cos(f + w) + ecc * sp.cos(w))
    return modelo


#lc_params, time, fsigns, free_params, ld, *theta_j
def mini_transit(lc_params, time, fsigns, free_params, ld, *theta_j):
    #P, t0, radius, dist, inc = theta
    nfp = len(free_params)
    params = batman.TransitParams()
    if theta_j:
        params.per = theta_j[0]                       #orbital period in days
        params.w = theta_j[1]                        #longitude of periastron (in degrees)
        params.ecc = theta_j[2]                      #eccentricity
    else:
        params.per = nfplc_params[nfp+ld]                       #orbital period in days
        params.w = nfplc_params[nfp+ld+1]                        #longitude of periastron (in degrees)
        params.ecc = nfplc_params[nfp+ld+2]                      #eccentricity
    params.t0 = nfplc_params[0]                       #time of inferior conjunction
    params.rp = nfplc_params[1]                   #planet radius (in units of stellar radii)
    params.a = nfplc_params[2]                      #semi-major axis (in units of stellar radii)
    params.inc = nfplc_params[3]                     #orbital inclination (in degrees)
    u = []
    for i in range(ld):
        u.append(nfplc_params[nfp+i])
    params.u = u                #limb darkening coefficients [u1, u2]
    params.limb_dark = "quadratic"       #limb darkening model

    m = batman.TransitModel(params, time)    #initializes model
    flux = m.light_curve(params)          #calculates light curve

    return (flux)


def pm_model(subtheta, P, time):
     #T0, r, a, b, c = param
    print('transit1')  # PMPMPM
    T0, r = subtheta
    # (t0 radius dist inc), P, time, fsigns
    lc_params = T0, r, 101.1576001138329, 89.912
    transit = transit_lightCurve(lc_params, P, time, fsigns)  # que es cada uno
    #t = time - time[0]
    #print transit, 'transit2\n\n'  # PMPMPM
    return transit #+ a + b*t + c*t*t


def henshin(thetas, kplanets):
    for i in range(kplanets):
        Pk = thetas[:, i*5]
        Ask = thetas[:, i*5 + 1]
        Ack = thetas[:, i*5 + 2]
        Sk = thetas[:, i*5 + 3]
        Ck = thetas[:, i*5 + 4]

        Ak = Ask ** 2 + Ack ** 2
        Phasek = sp.arccos(Ack / (Ak ** 0.5))

        ecck  = Sk ** 2 + Ck ** 2
        wk = sp.arccos(Ck / (ecck ** 0.5))
        for j in range(len(Sk)):
            if Sk[j] < 0:
                wk[j] = 2 * sp.pi - sp.arccos(Ck[j] / (ecck[j] ** 0.5))
            if Ask[j] < 0:
                Phasek[j] = 2 * sp.pi - sp.arccos(Ack[j] / (Ak[j] ** 0.5))

        thetas[:, i*5] = sp.exp(Pk)
        thetas[:, i*5 + 1] = Ak
        thetas[:, i*5 + 2] = Phasek
        thetas[:, i*5 + 3] = ecck
        thetas[:, i*5 + 4] = wk
    return thetas

def henshin_hou(thetas, kplanets, tags, fixed_values, anticoor):
    try:
        for t in range(len(thetas)):
            for i in range(len(anticoor)):
                thetas[t] = sp.insert(thetas[t], anticoor[i], fixed_values[anticoor[i]], axis=1)
    except:  # RAW
        for i in range(len(anticoor)):
            thetas = sp.insert(thetas, anticoor[i], fixed_values[anticoor[i]], axis=2)
    for t in range(len(thetas)):
        for i in range(kplanets):
            if tags[i][0]:
                Pk = sp.exp(thetas[t][:, i*5])
                thetas[t][:, i*5] = Pk
                print('changed period! (devs note)')
            if tags[i][1]:
                Ask = thetas[t][:, i*5 + 1]
                Ack = thetas[t][:, i*5 + 2]
                Ak = Ask ** 2 + Ack ** 2
                Phasek = sp.where(Ask>=0, sp.arccos(Ack / (Ak ** 0.5)), 2*sp.pi - sp.arccos(Ack / (Ak ** 0.5)))
                thetas[t][:, i*5 + 1] = Ak
                thetas[t][:, i*5 + 2] = Phasek
                print('changed amplitude! (devs note)')
            if tags[i][2]:
                Sk = thetas[t][:, i*5 + 3]
                Ck = thetas[t][:, i*5 + 4]
                ecck  = Sk ** 2 + Ck ** 2
                wk = sp.where(Sk>=0, sp.arccos(Ck / (ecck ** 0.5)), 2*sp.pi - sp.arccos(Ck / (ecck ** 0.5)))
                thetas[t][:, i*5 + 3] = ecck
                thetas[t][:, i*5 + 4] = wk
                print('changed eccentricity! (devs note)')

    return thetas

def nano_henshin_hou(thetas, kplanets, tags, fixed_values, anticoor):
    t2 = sp.ones_like(thetas)
    for i in range(kplanets):
        if tags[i][0]:
            t2[i*5] = sp.exp(thetas[i*5])
            print('changed period! (devs note)')
        if tags[i][1]:
            Ask = thetas[i*5 + 1]
            Ack = thetas[i*5 + 2]
            Ak = Ask ** 2 + Ack ** 2
            Phasek = sp.where(Ask>=0, sp.arccos(Ack / (Ak ** 0.5)), 2*sp.pi - sp.arccos(Ack / (Ak ** 0.5)))
            t2[i*5 + 1] = Ak
            t2[i*5 + 2] = Phasek
            print('changed amplitude! (devs note)')
        if tags[i][2]:
            Sk = thetas[i*5 + 3]
            Ck = thetas[i*5 + 4]
            ecck  = Sk ** 2 + Ck ** 2
            wk = sp.where(Sk>=0, sp.arccos(Ck / (ecck ** 0.5)), 2*sp.pi - sp.arccos(Ck / (ecck ** 0.5)))
            t2[i*5 + 3] = ecck
            t2[i*5 + 4] = wk
            print('changed eccentricity! (devs note)')
    for i in range(len(thetas))[5*kplanets:]:
        t2[i] = thetas[i]
    return thetas


def RV_residuals(theta, rv, time, ins, staract, starflag, kplanets, nins, MOAV, totcornum, ACC):
    ndat = len(time)
    model_params = kplanets * 5
    acc_params = ACC
    ins_params = 2 * (sp.sum(MOAV) + nins)
    jitter, offset, macoef, timescale = sp.zeros(ndat), sp.zeros(ndat), sp.array([sp.zeros(ndat) for i in range(MOAV)]), sp.array([sp.zeros(ndat) for i in range(MOAV)])
    if PACC:
        ACC = theta[model_params] * (time - time[0]) + theta[model_params + 1] * (time - time[0]) ** 2
    else:
        ACC = theta[model_params] * (time - time[0])

    residuals = sp.zeros(ndat)
    for i in range(ndat):
        jitpos = int(model_params + acc_params + ins[i] * 2 * (MOAV+1))
        jitter[i], offset[i] = theta[jitpos], theta[jitpos + 1]  # jitt
        for j in range(MOAV):
            macoef[j][i], timescale[j][i] = theta[jitpos + 2*(j+1)], theta[jitpos + 2*(j+1) + 1]
    a1 = (theta[:model_params])

    if totcornum:
        COR = sp.array([sp.array([sp.zeros(ndat) for k in range(len(starflag[i]))]) for i in range(len(starflag))])
        SA = theta[model_params+acc_params+ins_params:]

        assert len(SA) == totcornum, 'error in correlations'
        AR = 0.0  # just to remember to add this
        counter = -1

        for i in range(nins):
            for j in range(len(starflag[i])):
                counter += 1
                passer = -1
                for k in range(ndat):
                    if starflag[i][j] == ins[k]:  #
                        passer += 1
                        COR[i][j][k] = SA[counter] * staract[i][j][passer]

        FMC = 0
        for i in range(len(COR)):
            for j in range(len(COR[i])):
                FMC += COR[i][j]
    else:
        FMC = 0

    MODEL = RV_model(a1, time, kplanets) + offset + ACC + FMC
    #print MODEL

    for i in range(ndat):
        residuals[i] = rv[i] - MODEL[i]
        for c in range(MOAV):
            if i > c:
                MA = macoef[c][i] * sp.exp(-sp.fabs(time[i-1-c] - time[i]) / timescale[c][i]) * residuals[i-1-c]
                residuals[i] -= MA
    return residuals


### P R I O R S  ###


### L I K E L I H O O D S ###

import george
from george import kernels
from george.modeling import Model


# should all go in library  # DEL
def uniform(x, lims, args):
    if lims[0] <= x <= lims[1]:
        return 0.
    else:
        return -sp.inf

def uniform_spe(x, lims, args):
    if lims[0] <= x <= lims[1]:
        return 0.
    else:
        return -sp.inf

def flat(x, lims, args):
    if lims[0] <= x <= lims[1]:
        return 0.0
    else:
        return -sp.inf

def jeffreys(x, lims, args):
    if lims[0] <= x <= lims[1]:
        return sp.log(x**-1 / (sp.log(lims[1]/lims[0])))
    else:
        return -sp.inf

def normal(x, lims, args):
    if lims[0] <= x <= lims[1]:
        mean, var = args[0], 2*args[1]
        return ( - (x - mean) ** 2 / var)
    else:
        return -sp.inf

def fixed(x, lims, args):
    if lims[0] <= x <= lims[1]:
        return 0.0
    else:
        return -sp.inf

def joined(x, lims, args):
    if lims[0] <= x <= lims[1]:
        return 0.0
    else:
        return -sp.inf

def hou_cov(x, y, lim):
    if x ** 2 + y ** 2 < lim:
        return 0.0
    else:
        return -sp.inf


D = {'uniform':uniform,
     'flat':flat,
     'jeffreys':jeffreys,
     'normal':normal,
     'uniform_spe':uniform_spe,
     'uniform_spe_a':uniform_spe,
     'uniform_spe_b':uniform_spe,
     'uniform_spe_c':uniform_spe,
     'uniform_spe_d':uniform_spe,
     'fixed':fixed,
     'joined':joined,
     'hou_cov':hou_cov
     }

def neo_logp_rv(theta, params, CHECK=False):
    _theta, ndim, C = params
    c, lp = 0, 0.
    for j in range(ndim):
        add_this = D[_theta[C[j]].prior](theta[j], _theta[C[j]].lims, _theta[C[j]].args)
        lp += add_this

        if CHECK:
            if add_this == -sp.inf:
                print(_theta[C[j]], theta[j], _theta[C[j]].lims)
        ## use cv for this
        if _theta[C[j]].cv:
            if _theta[C[j]].tag() == 'Amplitude':
                lp += D['uniform'](theta[j]**2+theta[j+1]**2, _theta[C[j]].args, None)
                if CHECK:
                    if D['uniform'](theta[j]**2+theta[j+1]**2, _theta[C[j]].args, None) == -sp.inf:
                        print(theta[j]**2+theta[j+1]**2, _theta[C[j]].args)
            elif _theta[C[j]].tag() == 'Eccentricity':
                lp += D['normal'](theta[j]**2+theta[j+1]**2, _theta[C[j]].args, [0., 0.1**2])
                if CHECK:
                    if D['uniform'](theta[j]**2+theta[j+1]**2, _theta[C[j]].args, [0., 0.1**2]) == -sp.inf:
                        print(theta[j]**2+theta[j+1]**2, _theta[C[j]].args)
    # add HILL criteria!!
    #G = 39.5  ##6.67408e-11 * 1.9891e30 * (1.15740741e-5) ** 2  # in Solar Mass-1 s-2 m3
    #MP = sp.zeros(kplanets)  # this goes in hill
    #SMA, GAMMA = sp.zeros(kplanets), sp.zeros(kplanets)
    return lp

def neo_logl_rv(theta, paramis):
    # PARAMS DEFINITIONS
    # lock and load 'em
    _t, AC, params = paramis

    time, rv, err = params[0], params[1], params[2]
    ins, staract, starflag = params[3], params[4], params[5]
    kplanets, nins, MOAV = params[6], params[7], params[8]
    MOAV_STAR, totcornum, ACC = params[9], params[10], params[11]
    i, lnl = 0, 0
    ndat = len(time)


    # THETA CORRECTION FOR FIXED THETAS
    for a in AC:
        theta = sp.insert(theta, a, _t[a].val)

    # count 'em  # this could be outside!!!!
    model_params = kplanets * 5
    ins_params = (nins + sp.sum(MOAV)) * 2


    gen_moav_params = MOAV_STAR * 2
    gen_params = ACC + gen_moav_params

    a1 = (theta[:model_params])  # keplerian
    a2 = theta[model_params:model_params+ACC]  # acc
    a3 = theta[model_params+ACC:model_params+gen_params]  # starmoav
    a4 = theta[model_params+gen_params:model_params+gen_params+ins_params]  # instr moav
    a5 = theta[model_params+gen_params+ins_params:]
    # keplerian
    residuals = rv - RV_model(a1, time, kplanets)

    # general
    residuals -= acc_model(a2, time, ACC)

    # instrumental
    jitter, offset = sp.zeros(ndat), sp.ones(ndat)*sp.inf
    macoef, timescale = sp.array([sp.zeros(ndat) for i in range(sp.amax(MOAV))]), sp.array([sp.zeros(ndat) for i in range(sp.amax(MOAV))])

    # quitar el for de esta wea... array plox, ademas no es necesario recorrer ndat
    for i in range(ndat):
        jitpos = int(model_params + gen_params + (ins[i] + sp.sum(MOAV[:int(ins[i])])) * 2)
        jitter[i], offset[i] = theta[jitpos], theta[jitpos + 1]  #
        for jj in range(MOAV[int(ins[i])]):
            macoef[jj][i] = theta[jitpos + 2*(jj+1)]
            timescale[jj][i] = theta[jitpos + 2*(jj+1) + 1]

    residuals -= offset

    # staract (instrumental)

    #if totcornum:
    for sa in range(totcornum):
        residuals[ins==starflag[sa]] -= a5[sa] * staract[sa]

    residuals = gen_model(a3, time, MOAV_STAR, residuals)
    #MODEL = RV_model(a1, time, kplanets) + offset + ACC + FMC

    # Instrumental MOAV
    for I in range(nins):
        t_I = time[ins==I]
        for i in range(len(t_I)):
            for c in range(MOAV[I]):
                if i > c:
                    MA = macoef[c][i] * sp.exp(-sp.fabs(t_I[i-1-c] - t_I[i]) / timescale[c][i]) * residuals[i-1-c]
                    residuals[i] -= MA
    #'''
    #if kplanets>0:
    inv_sigma2 = 1.0 / (err**2 + jitter**2)
    lnl = sp.sum(residuals ** 2 * inv_sigma2 - sp.log(inv_sigma2)) + sp.log(2*sp.pi) * ndat
    if True:
        if lnl == sp.inf:
            print('like failed')
    #raise Exception('deb')
    return -0.5 * lnl


def neo_logp_pm(theta, params, CHECK=False):
    _theta, ndim, C = params
    c, lp = 0, 0.

    for j in range(ndim):
        lp += D[_theta[C[j]].prior](theta[j], _theta[C[j]].lims, _theta[C[j]].args)
    return lp

def neo_logl_pm(theta, paramis):
    _t, AC, params = paramis
    time, flux, err = params[0], params[1], params[2]
    ins, kplanets, nins = params[3], params[4], params[5]
    # for linear, linear should be [1, 1]
    ld, batman_m, batman_p = params[6], params[7], params[8]
    gp, gaussian_processor = params[9], params[10]

    ndat = len(time)
    #logl_params = sp.array([self.time_pm, self.rv_pm, self.err_pm,
    #                        self.ins_pm, kplan, self.nins_pm])
    # 0 correct for fixed values
    theta1 = theta.astype(float)
    for a in AC:
        theta1 = sp.insert(theta1, a, _t[a].val)

    # 1 armar el modelo con batman, es decir, llamar neo_lc
    params_b = time, kplanets, ld, batman_m, batman_p

    if gaussian_processor:
        theta_b = theta1[:-len(gp)]
        theta_g = theta1[-len(gp):]

    else:
        theta_b = theta1
    model = neo_lightcurve(theta_b, params_b)
    # 2 calcular res
    PM_residuals = flux - model  # why some people do the *1e6  # DEL
    #raise Exception('Debug')

    # 3 invocar likelihood usando george (puede ser otra func),
    # pero lo haré abajo pq why not
    # 4 armar kernel, hacer GP(kernel), can this be done outside?!
    #theta_gp = theta1[-len(gp):]
    #theta_gp[1] = 10 ** theta_gp[1]  # for k_r in Matern32Kernel
    if gaussian_processor:
        #theta_g[-1] = 10.**theta_g[-1]
        gp.set_parameter_vector(theta_g)  # last <gp> params, check for fixed shit?
        #raise Exception('debug')
        # should be jitter with err
        #gp.compute(time, sp.sqrt(err**2+theta_gp[0]**2))
        gp.compute(time, err)  # hmm ?
        if gaussian_processor == 'george':
            return gp.lnlikelihood(PM_residuals, quiet=True)  # george
        if gaussian_processor == 'celerite':
            try:
                return gp.log_likelihood(PM_residuals)  # celerite
            except:
                return -sp.inf
    else:
        inv_sigma2 = 1.0 / (err**2)
        lnl = sp.sum(PM_residuals ** 2 * inv_sigma2 - sp.log(inv_sigma2)) + sp.log(2*sp.pi) * ndat
        if lnl == sp.inf:
            print('like failed')
        return -0.5 * lnl


    #this should go outside
    '''
    kernel = t1 ** 2 * kernels.ExpSquaredKernel(t2 ** 2)
    jitt = george.modeling.ConstantModel(sp.log((1e-4)**2.))
    gp = george.GP(kernel, mean=0.0, fit_mean=False, white_noise=jitt,
                   fit_white_noise=True)
    gp.compute(time)
    #likelihood
    gp.set_parameter_vector(p)
    return gp.lnlikelihood(flux, quiet=True)
    '''
    pass


def neo_lightcurve(theta, params):
    #['t0', 'Period', 'Planet Radius', 'SemiMajor Axis', 'Inclination',
    #         'Eccentricity', 'Longitude', 'LD coef']
    #_t, AC, params = params
    time, kplanets = params[0], params[1]
    ld, batman_m, batman_p = params[2], params[3], params[4]

    flux = sp.ones(len(time))
    #  thetas go in corrected

    for k in range(kplanets):
        np = int(sp.sum(ld[:k])) + 7 * k
        # no ser huaso, usar setattr(params, 'n', v)

        batman_p[k].t0 = theta[np]
        batman_p[k].per = theta[np + 1]
        batman_p[k].rp = theta[np + 2]
        batman_p[k].a = theta[np + 3]
        batman_p[k].inc = theta[np + 4]
        batman_p[k].ecc = theta[np + 5]
        batman_p[k].w = theta[np + 6]
        batman_p[k].u = theta[np + 7:np + 7 + ld[k]]
        flux *= batman_m[k].light_curve(batman_p[k])  # calculates light curve
    #raise Exception('dasd')  # DEL
    return flux


def neo_init_batman(t, ld_mod, ldn):
    '''
    initializes batman
    '''
    n = {'t0': 0., 'per': 1., 'rp': 0.1, 'a': 15.,
         'inc': 87., 'ecc':0., 'w':90.}
    params = batman.TransitParams()
    for x in n:
        setattr(params, x, n[x])
    params.limb_dark = ld_mod  # limb darkening model
    ld_coefs = sp.ones(ldn)  # dummy coefficients

    params.u = ld_coefs
    model = batman.TransitModel(params, t)
    return model, params

K = {'Constant': 2. ** 2,
     'ExpSquaredKernel': kernels.ExpSquaredKernel(metric=1.**2),
     'ExpSine2Kernel': kernels.ExpSine2Kernel(gamma=1.0, log_period=1.0),
     'Matern32Kernel': kernels.Matern32Kernel(2.)}

def neo_init_george(kernels):
    '''
    kernels should be a matrix
    rows +, columns *, ie
    [[k1, k2], [k3, k4]]
    k_out = c*k1*k2+c*k3*k4
    '''
    k_out = K['Constant']
    for func in kernels[0]:
        k_out *= K[func]
    for i in range(len(kernels)):
        if i == 0:
            pass
        else:
            k = K['Constant']
            for func in kernels[i]:
                k *= K[func]
            k_out += k
    #gp = george.GP(k_out)
    #should return gp but check for wn
    return k_out


def neo_update_kernel(theta, params):
    gp = george.GP(mean=0.0, fit_mean=False, white_noise=jitt)
    pass


import celerite
from celerite import terms as cterms

#  2 or sp.log(10.) ?
T = {'Constant': 1. ** 2,
     'RealTerm':cterms.RealTerm(log_a=2., log_c=2.),
     'ComplexTerm':cterms.ComplexTerm(log_a=2., log_b=2., log_c=2., log_d=2.),
     'SHOTerm':cterms.SHOTerm(log_S0=2., log_Q=2., log_omega0=2.),
     'Matern32Term':cterms.Matern32Term(log_sigma=2., log_rho=2.),
     'JitterTerm':cterms.JitterTerm(log_sigma=1e-8)}


def neo_init_terms(terms):
    t_out = T[terms[0][0]]
    for f in range(len(terms[0])):
        if f == 0:
            pass
        else:
            t_out *= T[terms[0][f]]

    for i in range(len(terms)):
        if i == 0:
            pass
        else:
            for f in range(len(terms[i])):
                if f == 0:
                    t = T[terms[i][0]]
                else:
                    t *= T[func]
            t_out += t
    return t_out

def neo_init_cgp(terms):
    return celerite.GP(terms)


def neo_logp_rvpm(theta, params, CHECK=False):
    _theta, ndim, C = params
    c, lp = 0, 0.
    for j in range(ndim):
        lp += D[_theta[C[j]].prior](theta[j], _theta[C[j]].lims, _theta[C[j]].args)
    return lp


def neo_logl_rvpm(theta, paramis, CHECK=False):
    _t, indexer, params = paramis
    AC, B, CV = indexer

    params_rv, params_pm = params[0], params[1]

    kplanets, nins, MOAV = params_rv[6], params_rv[7], params_rv[8]
    MOAV_STAR, totcornum, ACC = params_rv[9], params_rv[10], params_rv[11]

    # THETA CORRECTION FOR FIXED THETAS
    for a in AC:
        theta = sp.insert(theta, a, _t[a].val)

    # count 'em  # this could be outside!!!! # DEL
    all_rv = kplanets * 5
    all_rv += (nins + sp.sum(MOAV)) * 2
    all_rv += MOAV_STAR * 2
    all_rv += ACC

    # armar thetas
    theta_rv = theta[:all_rv]  # DEL
    theta_pm = theta  # DEL
    for b in B:
        theta_pm = sp.insert(theta_pm, b[0], theta[b[1]])
    theta_pm = theta_pm[all_rv:]  # DEL

    #t0, per, pr, sma, inc, ecc, w
    # per, amp, pha, ecc, w
    x = sp.array([(True, False, False, True, True) for _ in range(kplanets)]).reshape(-1)
    x1 = sp.arange(len(x))
    xx = x1[x]


    #raise Exception('deb')

    #ndim_rv = 5*kplanets + 2*nins*(MOAV+1) + (1 + PACC) + totcornum
    #theta_rv = theta[:ndim_rv]
    #P = sp.array([theta[5*k] for k in range(kplanets)])
    #theta_pm = theta[ndim_rv:]
    logl_params_rv = [_t, AC, params_rv]
    logl_params_pm = [_t, AC, params_pm]

    LOGL_RV = neo_logl_rv(nano_henshin_hou(theta_rv, kplanets, CV, _t.list('val'), AC), logl_params_rv)
    if CHECK:
        print('loglrv', LOGL_RV)
    #raise Exception('deb')
    LOGL_PM = neo_logl_pm(theta_pm, logl_params_pm)
    if CHECK:
        print('loglpm', LOGL_PM)
    #print('pass2')
    return LOGL_RV + LOGL_PM






#
