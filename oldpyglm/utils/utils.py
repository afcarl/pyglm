import numpy as np
from scipy.linalg import solve, det, inv
from numpy import prod, diag, log, einsum, diag_indices, exp
from numpy.linalg import slogdet

def logistic(x):
    return 1./(1+exp(-x))

def logit(p):
    return log(p/(1-p))

def invert_low_rank(Ainv, U, C, V, diag=False):
    """
    Invert the matrix (A+UCV) where A^{-1} is known and C is lower rank than A

    Let N be rank of A and K be rank of C where K << N

    Then we can write the inverse,
    (A+UCV)^{-1} = A^{-1} - A^{-1}U (C^{-1}+VA^{-1}U)^{-1} VA^{-1}

    :param Ainv: NxN matrix A^{-1}
    :param U: NxK matrix
    :param C: KxK invertible matrix
    :param V: KxN matrix
    :return:
    """
    N,K = U.shape
    Cinv = inv(C)
    if diag:
        assert Ainv.shape == (N,)
        tmp1 = einsum('ij,j,jk->ik', V, Ainv, U)
        tmp2 = einsum('ij,j->ij', V, Ainv)
        tmp3 = solve(Cinv + tmp1, tmp2)
        # tmp4 = -U.dot(tmp3)
        tmp4 = -einsum('ij,jk->ik', U, tmp3)
        tmp4[diag_indices(N)] += 1
        return einsum('i,ij->ij', Ainv, tmp4)

    else:
        tmp = solve(Cinv + V.dot(Ainv).dot(U), V.dot(Ainv))
        return Ainv - Ainv.dot(U).dot(tmp)

def quad_form_diag_plus_lr(x, d, U, C, V):
    """
    Compute the quadratic form: x^T Q^{-1} x where Q = (diag(d) + UCV
    By the matrix inversion lemma, we can avoid computing matrix prods
    with the full rank matrix

    :param x:
    :param d:
    :param U:
    :param C:
    :param V:
    :return:
    """
    N,K = U.shape
    Cinv = inv(C)

    assert d.shape == (N,)
    D = 1.0/d


    # Compute x^T D
    xD = x*D                                # N
    # Compute x^T D x
    xDx = einsum('i,i', xD, x)              # 1 x 1

    # Compute the inner terms
    VDx = einsum('ij,j->i', V, xD)          # K x 1
    xDU = einsum('i,ij->j', xD,U)           # 1 x K
    VDU = einsum('ij,j,jk->ik', V, D, U)    # K x K
    WVDx = solve(Cinv + VDU, VDx)           # K x 1
    xDUWVDx = einsum('i,i', xDU, WVDx) # 1 x 1

    return xDx - xDUWVDx

def quad_form_diag_plus_lr2(x, d, U, C, V):
    return x.dot(solve_diagonal_plus_lowrank(d,U,C.dot(V),x))

# from pykalmanfilters
def solve_diagonal_plus_lowrank(diag_of_A,B,C,b):
    '''
    like np.linalg.solve(np.diag(diag_of_A)+B.dot(C),b) but better!
    b can be a matrix
    see p.673 of Convex Optimization by Boyd and Vandenberghe
    '''
    na = np.newaxis
    one_dim = b.ndim == 1
    if one_dim:
        b = np.reshape(b,(-1,1))
    z = b/diag_of_A[:,na]
    E = C.dot(B/diag_of_A[:,na])
    E.flat[::E.shape[0]+1] += 1
    w = np.linalg.solve(E,C.dot(z))
    z -= B.dot(w)/diag_of_A[:,na]
    return z if not one_dim else z.ravel()

def det_low_rank(Ainv, U, C, V, diag=False):
    """

    det(A+UCV) = det(C^{-1} + V A^{-1} U) det(C) det(A).

    :param Ainv: NxN
    :param U: NxK
    :param C: KxK
    :param V: KxN
    :return:
    """
    Cinv = inv(C)

    if diag:
        detA = 1.0 / prod(Ainv)
    else:
        detA = 1.0 / det(Ainv)

    return det(Cinv + V.dot(Ainv).dot(U)) * det(C) * detA

def logdet_low_rank(Ainv, U, C, V, diag=False):
    """

    logdet(A+UCV) = logdet(C^{-1} + V A^{-1} U) +  logdet(C) + logdet(A).

    :param Ainv: NxN
    :param U: NxK
    :param C: KxK
    :param V: KxN
    :return:
    """
    Cinv = inv(C)
    sC, ldC = slogdet(C)
    assert sC > 0

    if diag:
        ldA = -log(Ainv).sum()

        tmp1 = einsum('ij,j,jk->ik', V, Ainv, U)
        s1, ld1 = slogdet(Cinv + tmp1)
        assert s1 > 0

    else:
        sAinv, ldAinv = slogdet(Ainv)
        ldA = -ldAinv
        assert sAinv > 0

        s1, ld1 = slogdet(Cinv + V.dot(Ainv).dot(U))
        assert s1 > 0

    return  ld1 + ldC + ldA

def logdet_low_rank2(Ainv, U, C, V, diag=False):
    '''
    computes logdet(A+UCV) using https://en.wikipedia.org/wiki/Matrix_determinant_lemma
    '''
    if diag:
        ldA = -log(Ainv).sum()
        temp = C.dot(V).dot(U * Ainv[:,None])
    else:
        ldA = -slogdet(Ainv)[1]
        temp = C.dot(V).dot(Ainv).dot(U)
    temp.flat[::temp.shape[0]+1] += 1
    return slogdet(temp)[1] - log(Ainv).sum()
