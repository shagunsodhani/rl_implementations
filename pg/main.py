#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

import gym
import numpy as np
import torch
from torch import optim
from torch import tensor
from torch.distributions.categorical import Categorical
from torch.nn import Linear, ReLU, Sequential, Softmax

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--iterations", type=int, default=10 ** 3)
parser.add_argument("-d", "--discount", type=float, default=0.9999)
parser.add_argument("-e", "--env", type=str, default="CartPole-v0")

args = parser.parse_args()

DISCOUNT = args.discount
NUM_EPISODES = args.iterations

env = gym.make(args.env)

state_size = int(np.prod(env.observation_space.shape))
action_size = int(env.action_space.n)
hidden_size = 50

S, A, H = state_size, action_size, hidden_size

# for discrete action spaces only
actor = Sequential(
    Linear(S, H), ReLU(), Linear(H, H), ReLU(), Linear(H, A), Softmax(dim=None)
)

# Value function
critic = Sequential(Linear(S, H), ReLU(), Linear(H, H), ReLU(), Linear(H, 1))

opt = optim.Adam(list(actor.parameters()) + list(critic.parameters()))


def G(rewards, start=0, end=None):
    return sum(rewards[start:end])


if __name__ == "__main__":

    for episode in range(NUM_EPISODES):
        s, done = env.reset(), False
        states, rewards, log_probs = [], [], []

        while not done:
            s = torch.from_numpy(s).float()
            p = Categorical(actor(s))
            a = p.sample()
            with torch.no_grad():
                succ, r, done, _ = env.step(a.numpy())

            states.append(s)
            rewards.append(r)
            log_probs.append(p.log_prob(a))

            s = succ

        discounted_rewards = [DISCOUNT ** t * r for t, r in enumerate(rewards)]
        cumulative_returns = [
            G(discounted_rewards, t) for t, _ in enumerate(discounted_rewards)
        ]

        states = torch.stack(states)
        state_values = critic(states).reshape(-1)

        cumulative_returns = tensor(cumulative_returns)
        Adv = cumulative_returns - state_values

        log_probs = torch.stack(log_probs).reshape(-1)

        loss = -(Adv @ log_probs) / len(rewards)
        if episode > 500 and loss.item() < -1000:
            # TODO(alok): XXX rm
            from pudb import set_trace

            set_trace(paused=True)

        loss.backward()
        opt.step()
        opt.zero_grad()

        print(f"E: {episode+1}, R: {sum(rewards)}")
