'''
Denoising AutoEncoder Implementation that incorporates contextual group and venue data
'''
from __future__ import print_function, division  # Python2/3 Compatability

import os

from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.utils import shuffle
from tensorflow.contrib.layers import fully_connected

import aeer.dataset.event_dataset as ds
import aeer.dataset.user_group_dataset as user_group_ds
import numpy as np
import tensorflow as tf

os.environ['CUDA_VISIBLE_DEVICES'] = '3'


class ContextualAutoEncoder(object):

    def __init__(self, n_inputs, n_hidden, n_outputs, learning_rate=0.001):
        self.x = tf.placeholder(tf.float32, shape=[None, n_inputs])

        # We need to gather the indices from the matrix where our outputs are
        self.gather_indices = tf.placeholder(tf.int32, shape=[None, 2])

        self.y = tf.placeholder(tf.float32, shape=[None])

        # Weights
        W = tf.get_variable('W', shape=[n_inputs, n_hidden])
        b = tf.get_variable('Bias', shape=[n_hidden])

        # create hidden layer with default ReLU activation
        # fully_connected(self.x, n_hidden)
        hidden = tf.nn.relu(tf.nn.xw_plus_b(self.x, W, b))
        # hidden = tf.nn.relu(tf.add_n(tf.nn.xw_plus_b(self.x, W, b), self.venue_factor, self.group_factor))
        
        # add weight regularizer
        self.reg_scale = 0.01
        self.weights_regularizer = tf.nn.l2_loss(W, "weight_loss")
        # self.reg_loss = tf.reduce_sum(tf.abs(W))

        # create the output layer with no activation function
        self.outputs = fully_connected(hidden, n_outputs, activation_fn=None)

        self.targets = tf.gather_nd(self.outputs, self.gather_indices)

        self.actuals = tf.placeholder(tf.int32, shape=[None])

        # evaluate top k wrt outputs and actuals
        self.top_k = tf.nn.in_top_k(self.outputs, self.actuals, k=10)

        # square loss
        # self.loss = tf.losses.mean_squared_error(self.targets, self.y) + self.reg_scale * self.weights_regularizer
        self.loss = tf.losses.mean_squared_error(self.targets, self.y)
        optimizer = tf.train.AdamOptimizer(learning_rate)
        # Train Model
        self.train = optimizer.minimize(self.loss)


def main():
    n_epochs = 4
    n_hidden = 50
    NEG_COUNT = 4
    CORRUPT_RATIO = 0.1
    
    event_data = ds.EventData(ds.rsvp_chicago_file)
    users = event_data.get_users()
    events = event_data.get_events()
    venues = event_data.get_venues()
    groups = event_data.get_groups()
    
    n_inputs = len(events) + len(groups) + len(venues)
    n_outputs = len(events)
    model = ContextualAutoEncoder(n_inputs, n_hidden, n_outputs, learning_rate=0.001)

    init = tf.global_variables_initializer()

    tf_config = tf.ConfigProto(
        gpu_options=tf.GPUOptions(per_process_gpu_memory_fraction=0.25,
                                  allow_growth=True))

    with tf.Session(config=tf_config) as sess:
        init.run()
        for epoch in range(n_epochs):
            # additive gaussian noise or multiplicative mask-out/drop-out noise
            epoch_loss = 0.0
            users = shuffle(users)

            for user_id in users:
                x, y, item = event_data.get_user_train_events_with_context(user_id, NEG_COUNT, CORRUPT_RATIO)

                # We only compute loss on events we used as inputs
                # Each row is to index the first dimension
                gather_indices = list(zip(range(len(y)), item))

                # Get a batch of data
                batch_loss, _ = sess.run([model.loss, model.train], {
                    model.x: x.toarray().astype(np.float32),
                    model.gather_indices: gather_indices,
                    model.y: y
                })

                epoch_loss += batch_loss

            print("Epoch {:,}/{:<10,} Loss: {:,.6f}".format(epoch, n_epochs,
                                                            epoch_loss))

        # evaluate the model on the test set
        print("Evaluating model on test data")
        test_users = event_data.get_test_users()
        precision = 0
        valid_test_users = 0
        for user_id in test_users:
            # check if user was present in training data
            train_users = event_data.get_train_users()
            if user_id in train_users:
                valid_test_users = valid_test_users + 1
                unique_user_test_events = event_data.get_user_unique_test_events(user_id)
                test_event_index = [event_data._event_class_to_index[i] for i in unique_user_test_events]
                x, _, _ = event_data.get_user_train_events_with_context(user_id)

                # We replicate X, for the number of test events
                x = np.tile(x.toarray().astype(np.float32), (len(test_event_index), 1))
                # evaluate the model using the actuals
                top_k_events = sess.run(model.top_k, {
                    model.x: x,
                    model.actuals: test_event_index
                })

                precision = precision + np.sum(top_k_events)

        avg_precision = 0
        if (valid_test_users > 0):
            avg_precision = precision / valid_test_users

        print("Precision: {:,.6f}".format(avg_precision))


if __name__ == '__main__':
    main()
