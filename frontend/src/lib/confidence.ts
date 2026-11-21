/**
 * Below this the UI hides the name and asks for a clearer photo.
 *
 * Measured, not guessed. The species model picks from 7806 plants, so its
 * probabilities are spread far thinner than the 8-class model this replaced -
 * a top-1 of 0.42 is roughly 3000x above chance. On 1143 labelled photos:
 *
 *   threshold   shows a name   of those, correct
 *   0.50              20%             75%
 *   0.30              33%             67%
 *   0.20              45%             61%
 *
 * 0.50 left the app silent on photos where it actually knew the answer.
 * 0.30 trades some precision for three times the coverage; the percentage is
 * always shown next to the name, and the disclaimer is permanent.
 *
 * Keep in step with UNSURE_BELOW in backend/app/analyzer.py.
 */
export const CONFIDENCE_FLOOR = 0.3;
