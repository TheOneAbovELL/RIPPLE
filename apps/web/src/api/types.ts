/** Named shapes from the generated schema (`npm run gen:api`). Nothing here is hand-written
 * structure: every alias points at `components["schemas"]`, so a backend change that
 * reaches openapi.json fails type-checking here instead of failing silently in the UI. */
import type { components, paths } from "./schema";

type Schemas = components["schemas"];

export type Memory = Schemas["Memory"];
export type MemoryStatus = Schemas["Status"];
export type StructuredFact = Schemas["StructuredFact"];
export type Link = Schemas["Link"];
export type ChangeEvent = Schemas["ChangeEvent"];
export type Decision = Schemas["Decision"];
export type ForgetEvent = Schemas["ForgetEvent"];
export type MemoryOut = Schemas["MemoryOut"];
export type MemoriesOut = Schemas["MemoriesOut"];
export type MemoryDetailOut = Schemas["MemoryDetailOut"];
export type ParentOut = Schemas["ParentOut"];
export type HistoryOut = Schemas["HistoryOut"];
export type EditIn = Schemas["EditIn"];
export type IntakeOut = Schemas["IntakeOut"];
export type ForgetOut = Schemas["ForgetOut"];
export type QuestionOut = Schemas["QuestionOut"];
export type QuestionsOut = Schemas["QuestionsOut"];
export type AnswerIn = Schemas["AnswerIn"];
export type AnswerOut = Schemas["AnswerOut"];
export type RecommendationOut = Schemas["RecommendationOut"];
export type RecommendationsOut = Schemas["RecommendationsOut"];
export type MeOut = Schemas["MeOut"];
export type ExportOut = Schemas["ExportOut"];
export type GraphOut = Schemas["GraphOut"];
export type VocabularyOut = Schemas["VocabularyOut"];
export type LinkTypeOut = Schemas["LinkTypeOut"];
export type Feedback = Schemas["Feedback"];
export type FeedbackIn = Schemas["FeedbackIn"];
export type FeedbackKind = Schemas["FeedbackKind"];
export type FeedbackListOut = Schemas["FeedbackListOut"];

/** Query parameters GET /memories accepts, taken from the path's own definition. */
export type ListMemoriesQuery = NonNullable<paths["/memories"]["get"]["parameters"]["query"]>;
/** The statuses the list endpoint accepts: RETIRED is not one of them (I1, ADR-0042). */
export type VisibleStatus = NonNullable<ListMemoriesQuery["status"]>;
export type ChangeKind = Schemas["ChangeKind"];
export type DecisionAction = Schemas["DecisionAction"];
export type StatementIn = Schemas["StatementIn"];
export type LinkCodeOut = Schemas["LinkCodeOut"];
export type ResumeCandidate = Schemas["ResumeCandidate"];
export type CandidateStatus = Schemas["CandidateStatus"];
export type CandidatesOut = Schemas["CandidatesOut"];
export type CandidateOut = Schemas["CandidateOut"];
export type ConfirmOut = Schemas["ConfirmOut"];
export type ResumeUploadOut = Schemas["ResumeUploadOut"];
export type OpeningIn = Schemas["OpeningIn"];
export type OpeningOut = Schemas["OpeningOut"];
export type ParsedFieldOut = Schemas["ParsedFieldOut"];
export type ProfileAttributeOut = Schemas["ProfileAttributeOut"];
export type EventsOut = Schemas["EventsOut"];
export type EventMemoryOut = Schemas["EventMemoryOut"];

/** The filter GET /resume/candidates accepts ("all" included). */
export type CandidateFilter = NonNullable<
  NonNullable<paths["/resume/candidates"]["get"]["parameters"]["query"]>["status"]
>;
