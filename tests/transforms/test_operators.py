# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect
import copy

import numpy as np

import paddlers.transforms as T
from testing_utils import CpuCommonTest
from data import build_input_from_file

__all__ = ['TestTransform', 'TestCompose', 'TestArrange']

WHITE_LIST = ['ReloadMask']


def _add_op_tests(cls):
    """
    Automatically patch testing functions for transform operators.
    """

    for op_name in T.operators.__all__:
        op_class = getattr(T.operators, op_name)
        if isinstance(op_class, type) and issubclass(op_class,
                                                     T.operators.Transform):
            if op_class is T.DecodeImg or op_class in WHITE_LIST or op_name in WHITE_LIST:
                continue
            if issubclass(op_class, T.Compose) or issubclass(
                    op_class, T.operators.Arrange):
                continue
            attr_name = 'test_' + op_name
            if hasattr(cls, attr_name):
                continue
            # If the operator cannot be initialized with default parameters, skip it.
            for key, param in inspect.signature(
                    op_class.__init__).parameters.items():
                if key == 'self':
                    continue
                if param.default is param.empty:
                    break
            else:
                filter_ = OP2FILTER.get(op_name, None)
                setattr(
                    cls, attr_name, make_test_func(
                        op_class, filter_=filter_))
    return cls


def make_test_func(op_class,
                   *args,
                   in_hook=None,
                   out_hook=None,
                   filter_=None,
                   **kwargs):
    def _test_func(self):
        op = op_class(*args, **kwargs)
        decoder = T.DecodeImg()
        inputs = map(decoder, copy.deepcopy(self.inputs))
        for i, input_ in enumerate(inputs):
            if filter_ is not None:
                input_ = filter_(input_)
            with self.subTest(i=i):
                for sample in input_:
                    if in_hook:
                        sample = in_hook(sample)
                    sample = op(sample)
                    if out_hook:
                        sample = out_hook(sample)

    return _test_func


class _InputFilter(object):
    def __init__(self, conds):
        self.conds = conds

    def __call__(self, samples):
        for sample in samples:
            for cond in self.conds:
                if cond(sample):
                    yield sample

    def __or__(self, filter):
        return _InputFilter(self.conds + filter.conds)

    def __and__(self, filter):
        return _InputFilter(
            [cond for cond in self.conds if cond in filter.conds])

    def get_sample(self, input):
        return input[0]


def _is_optical(sample):
    return sample['image'].shape[2] == 3


def _is_sar(sample):
    return sample['image'].shape[2] == 1


def _is_multispectral(sample):
    return sample['image'].shape[2] > 3


def _is_mt(sample):
    return 'image2' in sample


def _is_seg(sample):
    return 'mask' in sample and 'image2' not in sample


def _is_det(sample):
    return 'gt_bbox' in sample or 'gt_poly' in sample


def _is_clas(sample):
    return 'label' in sample


_filter_only_optical = _InputFilter([_is_optical])
_filter_only_sar = _InputFilter([_is_sar])
_filter_only_multispectral = _InputFilter([_is_multispectral])
_filter_no_multispectral = _filter_only_optical | _filter_only_sar
_filter_no_sar = _filter_only_optical | _filter_only_multispectral
_filter_no_optical = _filter_only_sar | _filter_only_multispectral
_filter_only_mt = _InputFilter([_is_mt])
_filter_no_det = _InputFilter([_is_seg, _is_clas, _is_mt])

OP2FILTER = {
    'RandomSwap': _filter_only_mt,
    'SelectBand': _filter_no_sar,
    'Dehaze': _filter_only_optical,
    'Normalize': _filter_only_optical,
    'RandomDistort': _filter_only_optical
}


@_add_op_tests
class TestTransform(CpuCommonTest):
    def setUp(self):
        self.inputs = [
            build_input_from_file(
                "data/ssst/test_optical_clas.txt",
                prefix="./data/ssst"),
            build_input_from_file(
                "data/ssst/test_sar_clas.txt",
                prefix="./data/ssst"),
            build_input_from_file(
                "data/ssst/test_multispectral_clas.txt",
                prefix="./data/ssst"),
            build_input_from_file(
                "data/ssst/test_optical_seg.txt",
                prefix="./data/ssst"),
            build_input_from_file(
                "data/ssst/test_sar_seg.txt",
                prefix="./data/ssst"),
            build_input_from_file(
                "data/ssst/test_multispectral_seg.txt",
                prefix="./data/ssst"),
            build_input_from_file(
                "data/ssst/test_optical_det.txt",
                prefix="./data/ssst",
                label_list="data/ssst/labels_det.txt"),
            build_input_from_file(
                "data/ssst/test_sar_det.txt",
                prefix="./data/ssst",
                label_list="data/ssst/labels_det.txt"),
            build_input_from_file(
                "data/ssst/test_multispectral_det.txt",
                prefix="./data/ssst",
                label_list="data/ssst/labels_det.txt"),
            build_input_from_file(
                "data/ssst/test_det_coco.txt",
                prefix="./data/ssst"),
            build_input_from_file(
                "data/ssmt/test_mixed_binary.txt",
                prefix="./data/ssmt"),
            build_input_from_file(
                "data/ssmt/test_mixed_multiclass.txt",
                prefix="./data/ssmt"),
            build_input_from_file(
                "data/ssmt/test_mixed_multitask.txt",
                prefix="./data/ssmt")
        ]   # yapf: disable

    def test_DecodeImg(self):
        decoder = T.DecodeImg(to_rgb=True)
        for i, input in enumerate(self.inputs):
            with self.subTest(i=i):
                for sample in input:
                    sample = decoder(sample)
                    # Check type
                    self.assertIsInstance(sample['image'], np.ndarray)
                    if 'mask' in sample:
                        self.assertIsInstance(sample['mask'], np.ndarray)
                    if 'aux_masks' in sample:
                        for aux_mask in sample['aux_masks']:
                            self.assertIsInstance(aux_mask, np.ndarray)
                    # TODO: Check dtype

    def test_Resize(self):
        TARGET_SIZE = (128, 128)

        def _in_hook(sample):
            self.image_shape = sample['image'].shape
            if 'mask' in sample:
                self.mask_shape = sample['mask'].shape
                self.mask_values = set(sample['mask'].ravel())
            if 'aux_masks' in sample:
                self.aux_mask_shapes = [
                    aux_mask.shape for aux_mask in sample['aux_masks']
                ]
                self.aux_mask_values = [
                    set(aux_mask.ravel()) for aux_mask in sample['aux_masks']
                ]
            return sample

        def _out_hook_not_keep_ratio(sample):
            self.check_output_equal(sample['image'].shape[:2], TARGET_SIZE)
            if 'image2' in sample:
                self.check_output_equal(sample['image2'].shape[:2], TARGET_SIZE)
            if 'mask' in sample:
                self.check_output_equal(sample['mask'].shape[:2], TARGET_SIZE)
                self.assertLessEqual(
                    set(sample['mask'].ravel()), self.mask_values)
            if 'aux_masks' in sample:
                for aux_mask in sample['aux_masks']:
                    self.check_output_equal(aux_mask.shape[:2], TARGET_SIZE)
                for aux_mask, amv in zip(sample['aux_masks'],
                                         self.aux_mask_values):
                    self.assertLessEqual(set(aux_mask.ravel()), amv)
            # TODO: Test gt_bbox and gt_poly
            return sample

        def _out_hook_keep_ratio(sample):
            def __check_ratio(shape1, shape2):
                self.check_output_equal(shape1[0] / shape1[1],
                                        shape2[0] / shape2[1])

            __check_ratio(sample['image'].shape, self.image_shape)
            if 'image2' in sample:
                __check_ratio(sample['image2'].shape, self.image_shape)
            if 'mask' in sample:
                __check_ratio(sample['mask'].shape, self.mask_shape)
            if 'aux_masks' in sample:
                for aux_mask, ori_aux_mask_shape in zip(sample['aux_masks'],
                                                        self.aux_mask_shapes):
                    __check_ratio(aux_mask.shape, ori_aux_mask_shape)
            # TODO: Test gt_bbox and gt_poly
            return sample

        test_func_not_keep_ratio = make_test_func(
            T.Resize,
            in_hook=_in_hook,
            out_hook=_out_hook_not_keep_ratio,
            target_size=TARGET_SIZE,
            keep_ratio=False)
        test_func_not_keep_ratio(self)
        test_func_keep_ratio = make_test_func(
            T.Resize,
            in_hook=_in_hook,
            out_hook=_out_hook_keep_ratio,
            target_size=TARGET_SIZE,
            keep_ratio=True)
        test_func_keep_ratio(self)

    def test_RandomFlipOrRotate(self):
        def _in_hook(sample):
            if 'image2' in sample:
                self.im_diff = (
                    sample['image'] - sample['image2']).astype('float64')
            elif 'mask' in sample:
                self.im_diff = (
                    sample['image'][..., 0] - sample['mask']).astype('float64')
            return sample

        def _out_hook(sample):
            im_diff = None
            if 'image2' in sample:
                im_diff = (sample['image'] - sample['image2']).astype('float64')
            elif 'mask' in sample:
                im_diff = (
                    sample['image'][..., 0] - sample['mask']).astype('float64')
            if im_diff is not None:
                self.check_output_equal(im_diff.max(), self.im_diff.max())
                self.check_output_equal(im_diff.min(), self.im_diff.min())
            return sample

        test_func = make_test_func(
            T.RandomFlipOrRotate,
            in_hook=_in_hook,
            out_hook=_out_hook,
            filter_=_filter_no_det)
        test_func(self)


class TestCompose(CpuCommonTest):
    pass


class TestArrange(CpuCommonTest):
    pass
