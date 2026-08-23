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
     
    
    
    

