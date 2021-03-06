# coding=utf-8
# Copyright 2020 The Trax Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Tests for trax.layers.research.efficient_attention."""

import jax
import numpy as np
from tensorflow import test

from trax import fastmath
from trax import shapes
import trax.layers as tl
from trax.layers.research import sparsity


class EfficientFeedForwardTest(test.TestCase):

  def test_blocksparse_ff_train(self):
    d_model = 1024
    num_experts = 64
    d_ff = d_model * 8
    x_shape = (3, 7, d_model)
    with fastmath.use_backend(fastmath.Backend.JAX):
      layer = sparsity.BlockSparseFF(
          d_ff=d_ff, num_experts=num_experts, temperature=0.7, mode='train')
      x = np.ones(x_shape).astype(np.float32)
      _, _ = layer.init(shapes.signature(x))
      y = layer(x)
      self.assertEqual(y.shape, x.shape)

  def test_blocksparse_ff_predict_equals_eval(self):
    d_model = 1024
    num_experts = 64
    d_ff = d_model * 8
    x_shape = (1, 1, d_model)
    temperature = 0.7
    with fastmath.use_backend(fastmath.Backend.JAX):
      x = np.ones(x_shape).astype(np.float32)
      input_signature = shapes.signature(x)
      common_kwargs = dict(
          d_ff=d_ff,
          num_experts=num_experts,
          temperature=temperature,
      )
      eval_model = sparsity.BlockSparseFF(
          mode='eval', **common_kwargs)
      weights, state = eval_model.init(input_signature)
      eval_out, _ = eval_model.pure_fn(
          x, weights, state, rng=jax.random.PRNGKey(0))
      pred_model = sparsity.BlockSparseFF(
          mode='predict', **common_kwargs)
      _, _ = pred_model.init(input_signature)
      pred_out, _ = pred_model.pure_fn(
          x, weights, state, rng=jax.random.PRNGKey(0))
      self.assertEqual(eval_out.shape, x.shape)
      # eval_out and pred_out should be identical.
      np.testing.assert_array_almost_equal(eval_out[0, 0, :], pred_out[0, 0, :])


class ReversibleReshapePermuteTest(test.TestCase):

  def test_reversible_permute(self):
    layer = sparsity.ReversibleReshapePermute()
    x = np.array([[1, 2, 3, 4, 5, 6, 7, 8],
                  [0, 1, 2, 3, 4, 5, 6, 7]])
    layer.init(shapes.signature(x))
    ys = layer(x)
    self.assertEqual(tl.to_list(ys), [
        [1, 3, 5, 7, 2, 4, 6, 8],
        [0, 2, 4, 6, 1, 3, 5, 7]])
    rev_x = layer.reverse(ys, weights=layer.weights)
    self.assertEqual(tl.to_list(x), tl.to_list(rev_x))


class ReversibleRandomPermuteTest(test.TestCase):

  def test_reversible_permute(self):
    layer = sparsity.ReversibleRandomPermute()
    x = np.array([[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                  [0, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0, 11, 12, 13],
                  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                  ])
    layer.init(shapes.signature(x))
    ys = layer(x)
    # this assert will fail once per ~87B runs, but it's okay
    self.assertNotEqual(tl.to_list(ys), tl.to_list(x))

    self.assertEqual(tl.to_list(ys[0]), tl.to_list(ys[2]))
    self.assertNotEqual(tl.to_list(ys[0]), tl.to_list(ys[1]))
    rev_x = layer.reverse(ys, weights=layer.weights)
    self.assertEqual(tl.to_list(x), tl.to_list(rev_x))


class LocallyConnectedDenseTest(test.TestCase):

  def test_simple_call(self):
    layer = sparsity.LocallyConnectedDense(2, 8)
    x = np.array([[2, 5, 3, 4],
                  [0, 1, 2, 3]])
    _, _ = layer.init(shapes.signature(x))

    y = layer(x)
    self.assertEqual(y.shape, (2, 16))


class ModularCausalAttentionTest(test.TestCase):

  def test_simple_call(self):
    layer = sparsity.ModularCausalAttention(
        d_feature=4, n_heads=2, n_modules=2)
    x = np.array([[[2, 5, 3, 4],
                   [0, 1, 2, 3],
                   [0, 1, 2, 3],]])
    _, _ = layer.init(shapes.signature(x))

    y = layer(x)
    self.assertEqual(y.shape, (1, 3, 4))

if __name__ == '__main__':
  test.main()
