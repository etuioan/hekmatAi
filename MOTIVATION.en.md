# Why this project?

*A personal note by Tenshira, who started the project. Translated from the German original in [MOTIVATION.md](MOTIVATION.md).*

Hi everyone!

Before I release our project as open source, I'd like to tell you a bit about how I ended up here and what thoughts are behind it.

I'm simply a curious person who likes to dream things up in my head. For a long time I would have described myself as someone who constantly has ideas but hardly ever puts any of them into practice. Someone who doesn't always know exactly what he's doing, but is curious anyway. Thanks to AI, I no longer just have crazy ideas, I also have a tool that helps me actually try them out.

I've always been drawn to swimming against the current. So I asked myself: Could you build a good alternative to LLMs? Something that works differently and might even be better than them in certain areas? Not necessarily an AI that can do everything better right away. First of all, something of its own that tries a different path.

## First attempt: my own neurons

My first idea was: What if I programmed neurons myself that connect to each other, group themselves on their own and keep developing through evolutionary processes? I even wanted to use weather data as an outside source of unpredictable influences. Back then I thought this would somehow make the process more natural. Of course, weather data doesn't automatically give you "true randomness", but that was roughly my line of thinking.

My hope was that with enough millions of artificial neurons, something interesting might eventually emerge. Something that comes into being without me explicitly programming it.

I have to admit, though: back then I hardly knew anything about neurons.

At some point the project became huge and the code more and more confusing. With that, I lost the motivation to keep going. At the same time I realized that there are long-established open source projects already working on questions like these.

While looking into the work of Alan Hodgkin and Andrew Huxley, I also realized how far back the mathematical description of single nerve cells goes – and how costly it can get to simulate many of them in biological detail. I had relied quite a lot on the idea that intelligence would somehow emerge from enough detail. But I didn't have a clear plan for that. So at some point I gave up on this approach.

## Second attempt: a society of agents

About half a year later came the next idea. That was shortly after the big hype around DeepSeek, when I was just starting to get more deeply into AI agents myself.

I wanted to build a small society of agents. They would share an environment, interact with each other, store knowledge and access each other's knowledge. My idea was: if several agents check, discuss and revise an answer, maybe something better comes out than from a single model.

Hallucinations were a big topic for me. I hoped the agents could point out each other's mistakes. Basically, this was my attempt to get more reliable results through collaboration and maybe also emergence.

In practice, though, the coordination was pretty painful. It took a lot of effort before anything useful came out at all. Besides, several agents agreeing doesn't mean an answer is correct. After a few days, or maybe weeks, I put this project aside for the time being too.

But I didn't stop completely.

## World models, JEPA and Active Inference

I kept experimenting and at some point landed on Yann LeCun and JEPA. Honestly, back then I didn't really understand his work or exactly how it works. An interview had made me curious, but being curious and understanding something are two different things.

After that I came across Karl Friston's free energy principle and active inference. What I found especially exciting was the question: How does an agent use its world model to perceive, learn and act?

This again led to a few small prototypes. For example, the idea of a home AI that learns its users' habits, develops expectations and deals with uncertainty. Or experiments with chess, where I wanted to try out what role uncertainty might play in decisions. I also thought about whether such approaches could be applied to stock prices.

That was fun. But they were mostly experiments and toys, not mature systems or evidence that my ideas work.

## Context switching and the "slices"

At some point I asked myself: Why don't I look more closely at what happens in my own everyday life? How do I think? How do I recognize what matters right now? And how do I manage to adjust to a new situation?

I kept coming back to the topic of **context switching**. On a walk I had several things on my mind at once. I was thinking about Luhmann's systems theory and the differences between systems, about a film title, then about hamburgers, CDs and discs. How exactly I got from one thought to the next, I can't say anymore. At some point the word context was simply there. I pictured it as slices (in German "Scheiben", which also means discs) in the brain. Each slice stands for a model or certain experiences. In a situation, several of these slices can fit together and overlap because they contain similar aspects.

There is some space between the slices, but they are connected by a kind of net, roughly like spider webs. The closer the topics are to each other, the closer the slices lie together in my imagination. So they can not only overlap, but also lie side by side and be linked to each other.

In my head this was a whole 3D world, kind of like a data center, haha. That's how I imagined that experiences are connected and that, depending on the situation, different connections become important. For now this is just my mental image of it, not a claim about how the brain is actually built.

Then I asked myself how our brain and context might be connected. How do we recognize which situation we're in right now, and how do we switch mentally to another one? I noticed that this switch isn't always easy for me. Sometimes I want to start doing something, but in my head I'm still somewhere else entirely. That's how, step by step, I ended up with the topic of context switching.

I have ADHD myself. When I want to study, it sometimes takes quite a while until I've really arrived at studying. I might already be sitting in front of my notes, but my thoughts are still everywhere. To me it sometimes feels as if I can't quite find, or can't hold on to, the right inner state for the situation.

That's my personal description of this experience, not a complete explanation of ADHD. But it led me to a question: How does a system actually choose which context is relevant right now, and how does it stay in it without becoming inflexible?

While reading about the effects of trauma, a related question came to me from a completely different direction. A sound can occur in a safe everyday situation and still trigger memories or alarm reactions connected to an earlier danger. What occupied me was how earlier experiences can influence the interpretation of a present situation.

I don't want to equate ADHD with post-traumatic stress disorder or reduce them to one shared problem. What interested me was the more general question: How do we distinguish between what is happening right now and what we expect or fear because of earlier experiences?

## Shared structures

My second thought was that many situations in our everyday life share common structures.

Waiting at the doctor's and waiting for the train are different situations. Still, in both cases I have to deal with waiting time, be patient and maybe keep myself busy somehow. At the same time, different rules apply: I behave differently in a waiting room than on a train platform.

So I imagine that an artificial agent wouldn't have to learn everything from scratch for every situation. Maybe it could reuse shared components and combine them differently depending on the context. A kind of general understanding of "waiting", complemented by knowledge about what you're waiting for, where, and under which conditions.

Whether our brain really organizes things exactly like this, I don't know. For me it's first of all an idea I want to work with while building an agent.

Social rules also fit into this line of thought for me. As small children we don't automatically know which behavior is expected in which environment. We learn a lot through observation, through our parents and through our own experiences. I'm interested in how an agent could learn such similarities and differences without me having to give it every single rule.

Then there's the idea of **anchors for a context switch**. Maybe certain signals or actions can help activate the right context. When driving a car, that could be getting in, touching the steering wheel or pressing the clutch. Which cues are enough for a system to recognize: Now this is a different situation, now I need different expectations and different behavior?

## The current approach

From questions like these comes my current approach: an agent that doesn't just collect experiences, but recognizes what situations have in common, reuses knowledge and learns which context fits right now.

I'm not claiming to have understood the brain or found a solution for artificial general intelligence. I want to try out my thoughts and find out which of them are any good. Maybe some will work. Maybe with others I'll realize once again that I'm completely wrong. That's part of it for me now.

That's exactly why I want to make the project open. I'd be happy if others take a look, ask questions, find mistakes or bring in their own ideas. I'm still learning and could really use support – even if that support means explaining to me why something can't work this way.

Sorry for the long text. I'm new to this GitHub game, but I'm serious about it. This time I want to get further than the next half-finished experiment.

Have fun with my agents. Maybe you'd like to help build a piece of it.
