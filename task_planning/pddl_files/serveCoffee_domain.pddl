; domain_strips_fixed_v4.pddl
(define (domain serve-coffee-strips)
  (:requirements :strips :typing)

  (:predicates
    (at        ?o ?l)      ; object ?o is at location or device ?l
    (holding   ?o)         ; robot is holding object ?o
    (arm-empty)            ; robot arm is empty
    (off       ?d)         ; device ?d is off
    (on        ?d)         ; device ?d is on
    (filled    ?m)         ; mug ?m is filled with coffee
    (open      ?c)         ; container ?c is open
    (closed    ?c)         ; container ?c is closed
    (surface   ?l)         ; place-on 대상
    (container ?c)         ; place-in 대상
  )

  ;; 1) 집기
  (:action pick-up
    :parameters (?o ?l)
    :precondition (and (at ?o ?l) (arm-empty))
    :effect (and (holding ?o) (not (at ?o ?l)) (not (arm-empty)))
  )

  ;; 2) 올려놓기 (머그 → 커피머신 또는 표면)
  (:action place-on
    :parameters (?o ?l)
    :precondition (and (holding ?o) (surface ?l))
    :effect (and (at ?o ?l) (arm-empty) (not (holding ?o)))
  )

  ;; 3) 커피머신 켜기 (머그가 머신 위에 있으면 filled)
  (:action turn-on
    :parameters (?d ?m)
    :precondition (and (off ?d) (at ?m ?d))
    :effect (and (on ?d) (not (off ?d)) (filled ?m))
  )

  ;; 4) 커피머신 끄기
  (:action turn-off
    :parameters (?d)
    :precondition (on ?d)
    :effect (and (off ?d) (not (on ?d)))
  )

  ;; 5) 냉장고 열기 (손이 비어 있어야 함)
  (:action open
    :parameters (?c)
    :precondition (and (closed ?c) (arm-empty))
    :effect (and (open ?c) (not (closed ?c)))
  )

  ;; 6) 냉장고 닫기
  (:action close
    :parameters (?c)
    :precondition (open ?c)
    :effect (and (closed ?c) (not (open ?c)))
  )

  ;; 7) 냉장고에 넣기
  (:action place-in
    :parameters (?o ?c)
    :precondition (and (holding ?o) (open ?c) (container ?c))
    :effect (and (at ?o ?c) (arm-empty) (not (holding ?o)))
  )
)
