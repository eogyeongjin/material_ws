; problem_strips_fixed_v4.pddl
(define (problem serveCoffee-Strips)
  (:domain serve-coffee-strips)

  (:objects
    mug             coffeemachine  countertop   fridge
  )

  (:init
    (at          mug          countertop)
    (off         coffeemachine)
    (closed      fridge)
    (arm-empty)
    (surface     countertop)
    (surface     coffeemachine)
    (container   fridge)
  )

  (:goal
    (and
      (filled mug)
      (at     mug fridge)
    )
  )
)
