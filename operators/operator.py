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
        # 1. 입력이 list인 경우 numpy 배열로 변환
        if isinstance(arr, list):
            arr = np.array(arr, dtype=np.float64)

        data_num = len(arr)
        num_slots = self._engine.num_slots()

        # 총 필요한 암호문(Ciphertext)의 개수 계산 (올림)
        num_ct = int(math.ceil(data_num / num_slots)) 

        ct_list = []

        # 2. Chunking 및 Padding 진행
        for i in range(num_ct):
            s = i * num_slots
            e = min(s + num_slots, data_num)

            # num_slots 크기의 0으로 채워진 빈 배열 생성 (패딩 역할)
            padded_arr = np.zeros(num_slots, dtype=np.float64)

            # 실제 데이터를 빈 배열의 앞부분에 덮어쓰기
            padded_arr[:(e - s)] = arr[s:e]

            # Message 생성 및 디바이스(GPU/CPU)로 데이터 이동
            msg = hn.Message(padded_arr)
            # msg.to(self._engine.device())

            # 암호화 수행
            ct = hn.Ciphertext(self._engine.context())
            self._engine.encryptor().encrypt(msg, self._engine.pk(), ct)

            ct_list.append(ct)

        # 3. HEData 객체로 반환
        # level은 첫 번째 암호문에서 가져오고, scale은 HEAAN 설정에 따라 적절한 값을 넣어주면 됨.
        level = ct_list[0].level if ct_list else 0
        scale = 0 # 임시 값 (HEAAN 파라미터나 상황에 맞게 변경 필요)

        return HEData(ciphertexts=ct_list, size=data_num, level=level, scale=scale)

    def decrypt(self, hedata, isreal: bool = True) -> list:
        result_list = []

        # 1. HEData 안에 들어있는 여러 개의 암호문을 순서대로 꺼냄
        for ct in hedata.ciphertexts():

            # 결과를 담을 빈 Message 객체 생성
            ret_msg = hn.Message(self._engine.log_slots())

            # 엔진의 복호화기(decryptor)와 비밀키(sk)를 사용해 찐 복호화 진행!
            self._engine.decryptor().decrypt(ct, self._engine.sk(), ret_msg)

            # GPU(또는 연산 장치)에 있는 데이터를 CPU(host)로 가져옴
            ret_msg.to_host()

            # 2. 실수(Real)인지 복소수(Complex)인지에 따라 numpy 배열로 변환
            if isreal:
                arr = np.array(ret_msg, dtype=np.float64)
            else:
                arr = np.array(ret_msg, dtype=np.complex128)

            # 반환 타입이 list이므로 리스트로 변환해서 합쳐줌
            result_list.extend(arr.tolist())

        # 3. 암호화할 때 억지로 늘렸던 0(패딩) 부분을 잘라냄
        # hedata.size()를 이용해 딱 원래 데이터 길이까지만 리턴!
        return result_list[:hedata.size()]

    def add(self, ct1: HEData, ct2: HEData) -> HEData:
        """
        두 HEData를 chunk-wise로 더한다.

        result[i] = ct1[i] + ct2[i]

        한쪽에만 존재하는 추가 chunk는 새 ciphertext로 복사한다.
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
                # 원본 ciphertext 객체를 그대로 참조하지 않고
                # 새 객체에 복사한다.
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
        HEData의 모든 ciphertext slot에 상수 con을 더한다.

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

    def add_many(self, ct_list:list):
        if len(ct_list) < 2:
            return ct_list[0]

        added = self.copy_new(ct_list[0])
        for i in range(1, len(ct_list)):
            added = self.add(added, ct_list[i])
        
        return added
        
    def sub(self, ct1, ct2):
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
                # 🚨 주의: Go 코드의 로직(단순 복사)을 따랐지만, 뺄셈이므로 evt.sub(0, ctxts2[i], res_ct) 가 수학적으로 맞을 수 있음
                result_ctxts.append(ctxts2[i])
            elif i >= ct_len2:
                result_ctxts.append(ctxts1[i])

        return HEData(ciphertexts=result_ctxts, size=size, level=level, scale=scale)

    def sub_const(self, ct, con: float):
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

    def mult(self, ct1, ct2):
        # 곱셈은 Go 코드 로직처럼 min을 사용해 교집합만큼만 수행
        size = min(ct1.size(), ct2.size())
        level = min(ct1.level(), ct2.level()) - 1 # 곱셈 후 보통 Level 1 감소
        scale = min(ct1.scale(), ct2.scale())

        ctxts1 = ct1.ciphertexts()
        ctxts2 = ct2.ciphertexts()
        ct_num = min(len(ctxts1), len(ctxts2))

        result_ctxts = []
        evt = self._engine.evaluator()
        context = self._engine.context()

        for i in range(ct_num):
            res_ct = hn.Ciphertext(context)
            # HEaaN의 최신 파이썬 API에서는 mult 호출 시 내부적으로 relin과 rescale이 처리
            evt.mult(ctxts1[i], ctxts2[i], res_ct)
            result_ctxts.append(res_ct)

        return HEData(ciphertexts=result_ctxts, size=size, level=level, scale=scale)

    def mult_const(self, ct, con: float):
        size = ct.size()
        level = ct.level() - 1 # 상수 곱셈 후에도 일반적으로 Level 감소
        scale = ct.scale()

        result_ctxts = []
        evt = self._engine.evaluator()
        context = self._engine.context()

        for c in ct.ciphertexts():
            res_ct = hn.Ciphertext(context)
            evt.mult(c, con, res_ct)
            result_ctxts.append(res_ct)

        return HEData(ciphertexts=result_ctxts, size=size, level=level, scale=scale)

    def rotation(self, ct, rot_steps: int):
        size = ct.size()
        level = ct.level()
        scale = ct.scale()

        result_ctxts = []
        evt = self._engine.evaluator()
        context = self._engine.context()

        for c in ct.ciphertexts():
            res_ct = hn.Ciphertext(context)
            # HEaaN에서는 left_rotate(또는 right_rotate) 메서드를 사용
            evt.left_rotate(c, rot_steps, res_ct) 
            result_ctxts.append(res_ct)

        return HEData(ciphertexts=result_ctxts, size=size, level=level, scale=scale)

    def do_bootstrapping(self, data:HEData, level:int):
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
    # def copy_new(
    #     self,
    #     data: HEData,
    # ) -> HEData:
    #     """
    #     HEData의 모든 ciphertext chunk를 복사하여
    #     새로운 HEData를 반환한다.

    #     HEaaN evaluator.add()는 결과를 output ciphertext에 기록하며
    #     반환값은 None이므로, 반환값이 아니라 out을 저장해야 한다.
    #     """

    #     if data is None:
    #         raise ValueError(
    #             "data must not be None"
    #         )

    #     ciphertexts = data.ciphertexts()

    #     if len(ciphertexts) == 0:
    #         raise ValueError(
    #             "data contains no ciphertexts"
    #         )

    #     evaluator = self._engine.evaluator()
    #     context = self._engine.context()

        # result_ciphertexts = []

        # for chunk_index, ciphertext in enumerate(
        #     ciphertexts
        # ):
        #     if ciphertext is None:
        #         raise ValueError(
        #             "ciphertext is None: "
        #             f"chunk_index={chunk_index}"
        #         )

        #     out = hn.Ciphertext(context)

        #     # out = ciphertext + 0
        #     #
        #     # 중요:
        #     # evaluator.add()의 반환값은 None이고,
        #     # 연산 결과는 out에 기록된다.
        #     evaluator.add(
        #         ciphertext,
        #         0.0,
        #         out,
        #     )

        #     result_ciphertexts.append(out)

        # return HEData(
        #     ciphertexts=result_ciphertexts,
        #     size=data.size(),
        #     level=data.level(),
        #     scale=data.scale(),
        # )

    def sum(self, data, output_one:bool=False): # 파이썬 네이밍 규칙(스네이크 표기법)에 맞춰서 함수명 소문자!
        evt = self._engine.evaluator()
        context = self._engine.context()

        ciphertexts = data.ciphertexts()
        log_slots = self._engine.log_slots()

        # 1. 첫 번째 암호문 복사 (In-place로 원본 데이터가 오염되는 것을 방지)
        # HEaaN 버전에 따라 hn.Ciphertext(기존객체)를 쓰거나 파이썬의 copy.deepcopy를 써야 할 수 있음
        sum_ctxt = hn.Ciphertext(ciphertexts[0]) 

        # 2. 여러 암호문이 있다면 하나로 뭉치기 (배열 간 덧셈)
        if len(ciphertexts) > 1:
            for i in range(1, len(ciphertexts)):
                evt.add(sum_ctxt, ciphertexts[i], sum_ctxt)

        # 3. 하나의 암호문 안에 있는 모든 슬롯의 값을 누적해서 더하기 (Tree 기반 덧셈)
        for i in range(log_slots):
            # 회전한 결과를 임시로 담을 암호문 객체 생성
            tmp_ct = hn.Ciphertext(context) 

            # 2의 i승만큼 왼쪽으로 회전 (1, 2, 4, 8, 16...)
            evt.left_rotate(sum_ctxt, 2**i, tmp_ct) 

            # 원래 암호문(sum_ctxt)과 회전된 암호문(tmp_ct)을 더해서 다시 sum_ctxt에 저장
            evt.add(sum_ctxt, tmp_ct, sum_ctxt)

        # 4. Go 코드 로직에 맞게 결과 세팅

        # 동일한 결과(sum_ctxt)를 복사해서 반환했으므로 동일하게 맞춰줌
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
        

        # 덧셈과 Rotation은 일반적으로 Level을 깎지 않으므로 원래 level을 유지s!
        return HEData(
            ciphertexts=result_ctxts, 
            size=data.size(), 
            level=data.level(), 
            scale=data.scale()
        )

    
