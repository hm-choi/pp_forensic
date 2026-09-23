"""Container holding one or more CKKS ciphertexts.

Adapted from the PP-STAT implementation by Hyunmin Choi, which was itself
ported from an earlier Go implementation.
Reference: H. Choi, "PP-STAT: An Efficient Privacy-Preserving Statistical
Analysis Framework Using Homomorphic Encryption," CIKM '25.
"""
import heaan as hn

class HEData:
    def __init__(self, ciphertexts:list[hn.Ciphertext], size, level, scale):
        self._ciphertexts = ciphertexts
        self._size        = size
        self._level       = level
        self._scale       = scale

    def size(self):
        return self._size
    
    def level(self):
        return self._level
    
    def scale(self):
        return self._scale
    
    def ciphertexts(self):
        return self._ciphertexts
     
    
    
    

