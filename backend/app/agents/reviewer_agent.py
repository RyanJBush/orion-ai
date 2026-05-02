from app.agents.contracts import AgentRequest, AgentResponse, ReasoningTrace


class ReviewerAgent:
    name = "reviewer"
    role = "reviewer"

    def review(self, request: AgentRequest) -> AgentResponse:
        candidate_output = str(request.context.get("candidate_output", "")).strip()
        criteria = request.context.get("criteria") or ["non-empty output", "step goal alignment"]
        passed = bool(candidate_output)

        findings = []
        if not candidate_output:
            findings.append("Output is empty.")
        if len(candidate_output) > 0 and request.goal.lower() not in candidate_output.lower():
            findings.append("Output may not explicitly mention the goal; manual verification suggested.")

        return AgentResponse(
            agent=self.name,
            role=self.role,
            status="completed",
            output={
                "approved": passed,
                "score": 0.9 if passed else 0.35,
                "criteria": criteria,
                "findings": findings,
                "candidate_output": candidate_output,
            },
            reasoning_trace=ReasoningTrace(
                summary="Reviewer validated output completeness and basic goal alignment checks.",
                confidence=0.74,
                tags=["quality-check", "validation"],
            ),
        )


reviewer_agent = ReviewerAgent()
