'use strict';

class ReportController {
    constructor({ courseModel, enrollmentModel }) {
        this.courseModel = courseModel;
        this.enrollmentModel = enrollmentModel;
    }

    /**
     * Two queries and an in-memory group-by, replacing the nested forEach with
     * manual pending counters. Output order now follows course id instead of
     * whichever callback happened to return first.
     */
    async financialReport() {
        const [courses, enrollments] = await Promise.all([
            this.courseModel.findAll(),
            this.enrollmentModel.findAllWithStudentAndPayment(),
        ]);

        const byCourse = new Map(
            courses.map((course) => [course.id, { course: course.title, revenue: 0, students: [] }]),
        );

        for (const enrollment of enrollments) {
            const entry = byCourse.get(enrollment.course_id);
            if (!entry) continue;

            if (enrollment.payment_status === 'PAID') {
                entry.revenue += enrollment.payment_amount;
            }
            entry.students.push({
                student: enrollment.student_name || 'Unknown',
                paid: enrollment.payment_amount || 0,
            });
        }

        return courses.map((course) => byCourse.get(course.id));
    }
}

module.exports = ReportController;
