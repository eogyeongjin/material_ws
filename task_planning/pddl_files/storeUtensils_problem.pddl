; problem.pddl
(define (problem storeUtensils)
  (:domain store-in-drawer)

  (:objects
    spoon fork table drawer
  )

  (:init
    (at        spoon table)
    (at        fork  table)
    (arm-empty)
    (closed    drawer)
  )

  (:goal
    (and
      (in spoon drawer)
      (in fork  drawer)
    )
  )
)
