"""Pure-function checks for is_student_eligible_for_job. No network, no DB.

Guards the bug that let ISTEC through: the students table has branch_id/course_id
UUIDs and expected_graduation_date, not branch/batch strings.
"""
from portal import is_student_eligible_for_job

CE = "54059cc3-3cbe-4726-a08a-5ca4bc8475db"   # student's branch
MECH = "1ec27d7d-19b1-460e-a937-eb41eef07850"
BE = "6d2aedff-3195-4369-b607-3b439e824465"

STUDENT = {
    "branch_id": CE, "course_id": BE, "expected_graduation_date": "2027-06-01",
    "cgpa": 8.17, "gender": "Male", "active_backlogs": 0, "number_of_backlogs": 0,
    "tenth_board_percent": 95.0, "twelfth_board_percent": 91.0,
}


def job(**el):
    return {"job_eligibilities": [el]}


def demo():
    ok = lambda j: is_student_eligible_for_job(j, STUDENT)[0]

    # baseline
    assert ok(job(course_id=BE, eligible_batches=[2027], eligible_branches=[CE, MECH]))

    # ISTEC: right batch, wrong branch -> must be rejected
    istec = job(course_id=BE, eligible_batches=[2027], eligible_branches=[MECH])
    assert not ok(istec)
    assert "Branch" in is_student_eligible_for_job(istec, STUDENT)[1]

    # branches nested under course_eligible_branches (Axis/Essence shape)
    assert ok(job(course_id=BE, eligible_batches=[2027],
                  eligible_branches=None, course_eligible_branches={"branches": [CE]}))
    assert not ok(job(course_id=BE, eligible_batches=[2027],
                      eligible_branches=None, course_eligible_branches={"branches": [MECH]}))

    # batch comes from the graduation year, ints in the job
    assert not ok(job(eligible_batches=[2026], eligible_branches=[CE]))
    assert not ok(job(eligible_batches=[2028], eligible_branches=[CE]))

    # cgpa, marks, gender, backlogs
    assert not ok(job(eligible_branches=[CE], min_gpa=9))
    assert ok(job(eligible_branches=[CE], min_gpa=8))
    assert not ok(job(eligible_branches=[CE], min_twelfth_marks=95))
    assert ok(job(eligible_branches=[CE], min_tenth_marks=75, min_twelfth_marks=75))
    assert not ok(job(eligible_branches=[CE], genders=["female"]))
    assert ok(job(eligible_branches=[CE], genders=["male", "female", "other"]))
    assert ok(job(eligible_branches=[CE], genders=[]))          # empty = open to all
    assert ok(job(eligible_branches=[CE], allow_backlogs=False))  # student has none

    backlogger = {**STUDENT, "active_backlogs": 2, "number_of_backlogs": 3}
    assert not is_student_eligible_for_job(job(allow_backlogs=False), backlogger)[0]
    assert not is_student_eligible_for_job(job(disallow_backlog_ever=True), backlogger)[0]
    assert not is_student_eligible_for_job(job(active_backlog_number=1), backlogger)[0]
    assert is_student_eligible_for_job(job(allow_backlogs=True, active_backlog_number=2), backlogger)[0]

    # course mismatch
    assert not ok(job(course_id="some-mca-uuid", eligible_branches=[CE]))

    # missing data must not silently drop jobs
    assert ok(job())
    assert ok({"job_eligibilities": []})
    assert is_student_eligible_for_job(job(eligible_branches=[MECH]), {})[0]

    print("eligibility OK")


if __name__ == "__main__":
    demo()
