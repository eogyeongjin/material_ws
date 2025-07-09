; domain.pddl
(define (domain store-in-drawer)
  (:requirements :strips)

  (:predicates
    (at      ?o ?l)    
    (in      ?o ?c)   
    (holding ?o)       
    (arm-empty)        
    (open    ?c)       
    (closed  ?c)       
  )

  (:action open
    :parameters (?c)
    :precondition (closed ?c)
    :effect (and
      (open   ?c)
      (not (closed ?c))
    )
  )

  (:action close
    :parameters (?c)
    :precondition (open ?c)
    :effect (and
      (closed ?c)
      (not (open ?c))
    )
  )

  (:action pick-up
    :parameters (?o ?l)
    :precondition (and
      (at        ?o ?l)
      (arm-empty)
    )
    :effect (and
      (holding   ?o)
      (not (at   ?o ?l))
      (not (arm-empty))
    )
  )

  (:action place-on
    :parameters (?o ?l)
    :precondition (holding ?o)
    :effect (and
      (at        ?o ?l)
      (arm-empty)
      (not (holding ?o))
    )
  )

  (:action place-in
    :parameters (?o ?c)
    :precondition (and
      (holding ?o)
      (open    ?c)
    )
    :effect (and
      (in      ?o ?c)
      (arm-empty)
      (not (holding ?o))
    )
  )
)
