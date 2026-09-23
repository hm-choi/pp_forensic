"""HEaaN engine setup: context, keys and bootstrapping.

Adapted from the PP-STAT implementation by Hyunmin Choi, which was itself
ported from an earlier Go implementation.
Reference: H. Choi, "PP-STAT: An Efficient Privacy-Preserving Statistical
Analysis Framework Using Homomorphic Encryption," CIKM '25.
"""
import heaan as hn
import numpy as np
import os


class HEEngine:
    def __init__(
        self,
        params=hn.ParameterPreset.FGb,
        device_type="cpu",       # "cpu" or "gpu"
        device_id=0,
        log_slots=15,
        setting_root="/root/heaan_setting/",
        separate_keys_by_slots=False,
        warmup_bootstrap=False,  # False is recommended on CPU
    ):
        self._params = params
        self._device_type = device_type.lower()
        self._device_id = device_id
        self._log_slots = log_slots
        self._num_slots = 2 ** log_slots
        self._warmup_enabled = warmup_bootstrap

        if self._device_type not in ("cpu", "gpu"):
            raise ValueError(
                f"device_type must be 'cpu' or 'gpu': {device_type}"
            )

        params_preset = str(params)[-3:]

        if separate_keys_by_slots:
            self._setting_dir_path = os.path.join(
                setting_root,
                params_preset,
                f"log_slots_{log_slots}",
            )
        else:
            self._setting_dir_path = os.path.join(
                setting_root,
                params_preset,
            )

        self._key_dir_path = os.path.join(
            self._setting_dir_path,
            "keys",
        ) + os.sep

        self._SK_name = "SK"

        self._context = None
        self._sk = None
        self._pk = None
        self._ect = None
        self._dct = None
        self._evt = None
        self._bts = None
        self._dt = None

        self.setup()

        print(
            f"\nHEAAN ENGINE LOAD SUCCESS "
            f"[device={self._device_type.upper()}]\n"
        )

    def pk(self):
        return self._pk

    def sk(self):
        return self._sk

    def params(self):
        return self._params

    def log_slots(self):
        return self._log_slots

    def num_slots(self):
        return self._num_slots

    def context(self):
        return self._context

    def encryptor(self):
        return self._ect

    def decryptor(self):
        return self._dct

    def evaluator(self):
        return self._evt

    def bootstrapping(self):
        return self._bts

    def device(self):
        return self._dt

    def is_gpu(self):
        return self._device_type == "gpu"

    def setup(self):
        if self.is_gpu():
            self._context = hn.make_context(
                self._params,
                {self._device_id},
            )

            self._dt = hn.Device(
                hn.DeviceType.GPU,
                self._device_id,
            )

        else:
            # The second argument may be optional depending on the HEaaN release
            try:
                self._context = hn.make_context(
                    self._params
                )
            except TypeError:
                self._context = hn.make_context(
                    self._params,
                    set(),
                )

            # CPU objects stay on the default device
            self._dt = None

        os.makedirs(
            self._key_dir_path,
            exist_ok=True,
        )

        print("Device:", self._device_type.upper())
        print("Key directory:", self._key_dir_path)

        self._load_keys()
        self._init_operators()

        if self._warmup_enabled:
            self._warmup_bootstrap()

        return self

    def _load_keys(self):
        sk_path = self._key_dir_path + self._SK_name

        try:
            self._sk = hn.SecretKey(
                self._context,
                sk_path,
            )

            self._pk = hn.KeyPack(
                self._context,
                self._key_dir_path,
            )

            print("Key loaded")

        except Exception as exc:
            print("Key load failed:", repr(exc))
            print("Generating new keys.")

            self._sk = hn.SecretKey(
                self._context
            )
            self._sk.save(sk_path)

            keygen = hn.KeyGenerator(
                self._context,
                self._sk,
            )

            keygen.gen_common_keys()
            keygen.gen_rot_keys_for_bootstrap(
                self._log_slots,
            )
            keygen.save(
                self._key_dir_path
            )

            self._pk = keygen.keypack

            print("Key generation done")

    def _init_operators(self):
        # Move objects to GPU only in GPU mode
        if self.is_gpu():
            self._sk.to(self._dt)
            self._pk.to(self._dt)

        self._ect = hn.Encryptor(
            self._context
        )
        self._dct = hn.Decryptor(
            self._context
        )

        self._evt = hn.HomEvaluator(
            self._context,
            self._pk,
        )

        self._bts = hn.Bootstrapper(
            self._evt
        )

    def _warmup_bootstrap(self):
        msg = hn.Message(
            np.zeros(
                self._num_slots,
                dtype=np.float64,
            )
        )

        # Move the Message only in GPU mode
        if self.is_gpu():
            msg.to(self._dt)

        ctxt = hn.Ciphertext(
            self._context
        )

        print(
            f"Warm-up encrypt start "
            f"[{self._device_type.upper()}]"
        )

        self._ect.encrypt(
            msg,
            self._pk,
            ctxt,
        )

        print("Warm-up encrypt done")
        print("Warm-up bootstrap start")

        self._bts.bootstrap(
            ctxt,
            ctxt,
        )

        print("Warm-up bootstrap done")