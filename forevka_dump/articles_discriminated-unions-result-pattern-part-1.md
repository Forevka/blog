# Discriminated Unions & Result Pattern

> Source: https://forevka.dev/articles/discriminated-unions-result-pattern-part-1/

---

# What Are Discriminated Unions and how it related to maintainable code 

Have you ever wondered how you can make your code both robust and beautiful? In the realm of functional programming, discriminated unions (also known as algebraic data types) offer a powerful way to represent data with clarity and precision. 

### What Are Discriminated Unions? 

Imagine you’re an artist with a **perfectly organized palette**. Each color is distinct, and you know exactly when and how to use it. Discriminated unions work similarly—they allow you to define a type that can be one of several distinct variants. Each variant can carry its own specific data, making the whole construct a clear, self-documenting model of your domain.

### A Simple Pseudocode Example: 

The Option Type Consider a common scenario: you want to represent a value that might or might not be present. In many languages, this is done using a nullable type, but discriminated unions take a more explicit approach:
    
    
    type Option<T> =
        | Some(value: T)
        | None

Isn’t it refreshing to know that an `Option` is always either `Some` value or `None `— there’s no room for ambiguity?

### A Philosophical Detour: Mathematics, Art, and Code

Let’s take a moment to appreciate the deeper roots of discriminated unions. In mathematics, there is the concept of a _disjoint union_ —a way of combining sets so that each element’s origin is preserved. This idea is as old as mathematics itself, reflecting a timeless desire for clarity and order.

**Programming, at its best, is much like art or philosophy**. Every time you choose a design pattern or a type system, you’re making a statement about how you wish to interact with the world. By opting for discriminated unions, you’re saying, “I value explicitness, safety, and elegance.” Isn’t it inspiring to think that your code can be a canvas where logic meets creativity?

* * *

### Pattern Matching: The Heartbeat of Functional Programming

Once you’ve defined a discriminated union, the next step is to work with it. Enter **pattern matching**. This is the functional programmer’s secret weapon: a way to deconstruct and handle each variant explicitly.

### A Pseudocode Example: Handling an Option
    
    
    function process(option: Option<T>) {
        match option {
            case Some(value):
                print("Found a value: " + value)
            case None:
                print("No value found.")
        }
    }

Ask yourself: wouldn’t it be comforting to know that every possible case is handled? That’s the promise of pattern matching—it forces you to consider all outcomes, leaving no room for forgotten edge cases.

### The Benefits: Clarity, Safety, and Joy

1\. Expressiveness and Self-Documentation

When you define a type with a discriminated union, you lay out all possible states right before your eyes. No hidden surprises. Every variant is explicitly named, making your code not only easier to understand but also easier to maintain.

2\. Exhaustive Checking

Languages that support discriminated unions often come with compilers that check for exhaustive handling. This means if you add a new variant, your compiler will cheerfully (or sometimes sternly) remind you to handle it everywhere. Can you imagine the relief of knowing that your compiler is looking out for you?

3\. Eliminating Null-Related Bugs

By modeling optional values with a type like `Option`, you force yourself to handle both the presence and absence of data explicitly. This approach virtually eliminates those annoying null pointer exceptions. Isn’t it time we said goodbye to those runtime gremlins?

* * *

### Discriminated Unions vs. Object-Oriented Polymorphism

In object-oriented programming, you might use polymorphism and inheritance to achieve similar behavior. However, discriminated unions offer a more straightforward and less error-prone alternative. Instead of navigating complex inheritance trees, you declare every possibility upfront.

A Pseudocode Example: Modeling Errors

Consider a system that can encounter different kinds of errors:
    
    
    type Error =
        | NotFound(message: String)
        | PermissionDenied(message: String)

Every time you handle an `Error`, you must account for both possibilities. There’s no chance for an unhandled error type to slip through the cracks.

* * *

_Are you ready to let your code reflect the precision of a mathematician and the creativity of an artist?_

We will continue journey with the unions in the next chapter of series