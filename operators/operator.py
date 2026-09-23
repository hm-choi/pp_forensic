"""Homomorphic operator wrappers over the HEaaN evaluator.

Adapted from the PP-STAT implementation by Hyunmin Choi, which was itself
ported from an earlier Go implementation.
Reference: H. Choi, "PP-STAT: An Efficient Privacy-Preserving Statistical
Analysis Framework Using Homomorphic Encryption," CIKM '25.
"""
from engine.engine import HEEngine
import heaan as hn
import numpy as np
from hedata.data import HEData
import math 
from . import bscount

class HEOperator:
    def __init__(self, engine:HEEngine):
        self._engine = engine 
       
    def encrypt(self, arr) -> HEData:
        # 1. Convert list input to a numpy array
        if isinstance(arr, list):
            arr = np.array(arr, dtype=np.float64)

        data_num = len(arr)
        num_slots = self._engine.num_slots()

        # Total number of ciphertexts needed, rounded up
        num_ct = int(math.ceil(data_num / num_slots)) 

        ct_list = []

        # 2. Chunk and pad
        for i in range(num_ct):
            s = i * num_slots
            e = min(s + num_slots, data_num)

            # Zero-filled buffer of num_slots (padding)
            padded_arr = np.zeros(num_slots, dtype=np.float64)

            # Copy the real data into the front of the buffer
            padded_arr[:(e - s)] = arr[s:e]

            # Build a Message and move it to the device (GPU/CPU)
            msg = hn.Message(padded_arr)
            # msg.to(self._engine.device())

            # Encrypt
            ct = hn.Ciphertext(self._engine.context())
            self._engine.encryptor().encrypt(msg, self._engine.pk(), ct)

            ct_list.append(ct)

        # 3. Return as an HEData object
        # level comes from the first ciphertext; scale follows the HEaaN setting.
        level = ct_list[0].level if ct_list else 0
        scale = 0 # placeholder (adjust to the HEaaN parameters)

        return HEData(ciphertexts=ct_list, size=data_num, level=level, scale=scale)

    def decrypt(self, hedata: HEData, isreal: bool = True) -> list:
        result_list = []

        # 1. Take the ciphertexts held in HEData in order
        for ct in hedata.ciphertexts():

            # Empty Message to receive the result
            ret_msg = hn.Message(self._engine.log_slots())

            # Decrypt with the engine decryptor and the secret key
            self._engine.decryptor().decrypt(ct, self._engine.sk(), ret_msg)

            # Move the data from the device back to the host
            ret_msg.to_host()

            # 2. Convert to a numpy array, real or complex
            if isreal:
                arr = np.array(ret_msg, dtype=np.float64)
            else:
                arr = np.array(ret_msg, dtype=np.complex128)

            # The return type is a list, so convert and concatenate
            result_list.extend(arr.tolist())

        # 3. Drop the zero padding added at encryption time
        # Return only up to the original length using hedata.size()
        return result_list[:hedata.size()]

    def add(self, ct1: HEData, ct2: HEData) -> HEData:
        """
        Add two HEData chunk-wise.

        result[i] = ct1[i] + ct2[i]

        A chunk present on only one side is copied into a new ciphertext.
        """

        if ct1 is None or ct2 is None:
            raise ValueError("ct1 and ct2 must not be None")

        size = max(ct1.size(), ct2.size())
        level = min(ct1.level(), ct2.level())
        scale = min(ct1.scale(), ct2.scale())

        ctxts1 = ct1.ciphertexts()
        ctxts2 = ct2.ciphertexts()

        ct_len1 = len(ctxts1)
        ct_len2 = len(ctxts2)
        ct_num = max(ct_len1, ct_len2)

        if ct_num == 0:
            raise ValueError("ct1 and ct2 contain no ciphertexts")

        result_ctxts = []

        evt = self._engine.evaluator()
        context = self._engine.context()

        for i in range(ct_num):
            res_ct = hn.Ciphertext(context)

            if i < ct_len1 and i < ct_len2:
                if ctxts1[i] is None or ctxts2[i] is None:
                    raise ValueError(f"None ciphertext at chunk {i}")

                evt.add(ctxts1[i],ctxts2[i],res_ct,)

            elif i < ct_len1:
                if ctxts1[i] is None:
                    raise ValueError(
                        f"ct1 ciphertext is None "
                        f"at chunk {i}"
                    )

                # res_ct = ctxts1[i]
                #
                # Do not reference the original ciphertext object;
                # copy it into a new one.
                evt.add(ctxts1[i],0.0,res_ct)

            else:
                if ctxts2[i] is None:
                    raise ValueError(f"ct2 ciphertext is None " f"at chunk {i}")

                # res_ct = ctxts2[i]
                evt.add(ctxts2[i],0.0,res_ct)

            result_ctxts.append(res_ct)

        return HEData(ciphertexts=result_ctxts,size=size,level=level,scale=scale)

    def add_const(
        self,
        ct: HEData,
        con: float,
    ) -> HEData:
        """
        Add the constant con to every ciphertext slot of HEData.

        result[i] = ct[i] + con

        Example
        -------
        ct:
            [1.0, 2.0, 3.0]

        con:
            5.0

        result:
            [6.0, 7.0, 8.0]
        """

        if ct is None:
            raise ValueError(
                "ct must not be None"
            )

        if not np.isfinite(con):
            raise ValueError(
                f"con must be finite: {con}"
            )

        size = ct.size()
        level = ct.level()
        scale = ct.scale()

        ciphertexts = ct.ciphertexts()

        if len(ciphertexts) == 0:
            raise ValueError(
                "ct contains no ciphertexts"
            )

        result_ctxts = []

        evt = self._engine.evaluator()
        context = self._engine.context()

        for chunk_index, ciphertext in enumerate(
            ciphertexts
        ):
            if ciphertext is None:
                raise ValueError(
                    "ciphertext is None: "
                    f"chunk_index={chunk_index}"
                )

            res_ct = hn.Ciphertext(context)

            evt.add(
                ciphertext,
                float(con),
                res_ct,
            )

            result_ctxts.append(res_ct)

        return HEData(
            ciphertexts=result_ctxts,
            size=size,
            level=level,
            scale=scale,
        )

    def sub(self, ct1: HEData, ct2: HEData) -> HEData:
        size = max(ct1.size(), ct2.size())
        level = min(ct1.level(), ct2.level())
        scale = min(ct1.scale(), ct2.scale())

        ctxts1 = ct1.ciphertexts()
        ctxts2 = ct2.ciphertexts()
        ct_len1 = len(ctxts1)
        ct_len2 = len(ctxts2)
        ct_num = max(ct_len1, ct_len2)

        result_ctxts = []
        evt = self._engine.evaluator()
        context = self._engine.context()

        for i in range(ct_num):
            if i < ct_len1 and i < ct_len2:
                res_ct = hn.Ciphertext(context)
                evt.sub(ctxts1[i], ctxts2[i], res_ct)
                result_ctxts.append(res_ct)
            elif i >= ct_len1:
                # NOTE: follows the Go logic (plain copy), but as this is a subtraction, evt.sub(0, ctxts2[i], res_ct) may be the mathematically correct form
                result_ctxts.append(ctxts2[i])
            elif i >= ct_len2:
                result_ctxts.append(ctxts1[i])

        return HEData(ciphertexts=result_ctxts, size=size, level=level, scale=scale)

    def sub_const(self, ct: HEData, con: float) -> HEData:
        size = ct.size()
        level = ct.level()
        scale = ct.scale()

        result_ctxts = []
        evt = self._engine.evaluator()
        context = self._engine.context()

        for c in ct.ciphertexts():
            res_ct = hn.Ciphertext(context)
            evt.sub(c, con, res_ct)
            result_ctxts.append(res_ct)

        return HEData(ciphertexts=result_ctxts, size=size, level=level, scale=scale)

    def mult(self, ct1: HEData, ct2: HEData) -> HEData:
        # Multiplication follows the Go logic: min covers only the intersection
        size = min(ct1.size(), ct2.size())
        level = min(ct1.level(), ct2.level()) - 1 # one level is usually consumed
        scale = min(ct1.scale(), ct2.scale())

        ctxts1 = ct1.ciphertexts()
        ctxts2 = ct2.ciphertexts()
        ct_num = min(len(ctxts1), len(ctxts2))

        result_ctxts = []
        evt = self._engine.evaluator()
        context = self._engine.context()

        for i in range(ct_num):
            res_ct = hn.Ciphertext(context)
            # Recent HEaaN Python APIs handle relinearization and rescaling inside mult
            evt.mult(ctxts1[i], ctxts2[i], res_ct)
            result_ctxts.append(res_ct)

        return HEData(ciphertexts=result_ctxts, size=size, level=level, scale=scale)

    def mult_const(self, ct: HEData, con: float) -> HEData:
        size = ct.size()
        level = ct.level() - 1 # constant multiplication also usually consumes a level
        scale = ct.scale()

        result_ctxts = []
        evt = self._engine.evaluator()
        context = self._engine.context()

        for c in ct.ciphertexts():
            res_ct = hn.Ciphertext(context)
            evt.mult(c, con, res_ct)
            result_ctxts.append(res_ct)

        return HEData(ciphertexts=result_ctxts, size=size, level=level, scale=scale)

    def rotation(self, ct: HEData, rot_steps: int) -> HEData:
        size = ct.size()
        level = ct.level()
        scale = ct.scale()

        result_ctxts = []
        evt = self._engine.evaluator()
        context = self._engine.context()

        for c in ct.ciphertexts():
            res_ct = hn.Ciphertext(context)
            # HEaaN uses left_rotate (or right_rotate)
            evt.left_rotate(c, rot_steps, res_ct) 
            result_ctxts.append(res_ct)

        return HEData(ciphertexts=result_ctxts, size=size, level=level, scale=scale)

    def do_bootstrapping(self, data: HEData, level: int) -> HEData:
        if data.level() <= level:
            print("bootstrapping!!")
            for i in range(len(data.ciphertexts())):
                self._engine.bootstrapping().bootstrap(data.ciphertexts()[i], data.ciphertexts()[i])  
                bscount.add_bootstrap()

        
        return HEData(data.ciphertexts(), data.size(), data.ciphertexts()[0].level, data.scale())

    def copy_new(self, data:HEData) -> HEData:
        ciphertexts = data.ciphertexts()
        result = []
        for i in range(len(ciphertexts)):
            result.append(hn.Ciphertext(ciphertexts[i]))
        return HEData(result, data.size(), data.level(), data.scale())
    def sum(self, data: HEData, output_one: bool = False) -> HEData: # lowercase name to follow the Python naming convention
        evt = self._engine.evaluator()
        context = self._engine.context()

        ciphertexts = data.ciphertexts()
        log_slots = self._engine.log_slots()

        # 1. Copy the first ciphertext (avoid in-place corruption of the original)
        # Depending on the HEaaN version this may need hn.Ciphertext(obj) or copy.deepcopy
        sum_ctxt = hn.Ciphertext(ciphertexts[0]) 

        # 2. If several ciphertexts exist, fold them into one
        if len(ciphertexts) > 1:
            for i in range(1, len(ciphertexts)):
                evt.add(sum_ctxt, ciphertexts[i], sum_ctxt)

        # 3. Accumulate every slot inside one ciphertext (tree based sum)
        for i in range(log_slots):
            # Temporary ciphertext to hold the rotated result
            tmp_ct = hn.Ciphertext(context) 

            # Rotate left by 2^i (1, 2, 4, 8, 16, ...)
            evt.left_rotate(sum_ctxt, 2**i, tmp_ct) 

            # Add the rotated ciphertext back into sum_ctxt
            evt.add(sum_ctxt, tmp_ct, sum_ctxt)

        # 4. Set the result to match the Go logic

        # The same sum_ctxt is copied and returned, so keep the fields consistent
        result_ctxts = []
        if output_one:
            result_ctxts = [hn.Ciphertext(sum_ctxt)]
            return HEData(
                        ciphertexts=result_ctxts, 
                        size=self._engine.num_slots(), 
                        level=data.level(), 
                        scale=data.scale()
                    )

        for _ in range(len(ciphertexts)):
            result_ctxts.append(hn.Ciphertext(sum_ctxt))
        

        # Addition and rotation do not consume a level, so keep the original level
        return HEData(
            ciphertexts=result_ctxts, 
            size=data.size(), 
            level=data.level(), 
            scale=data.scale()
        )

    
