import React from "react";
import Placeholder from "./_Placeholder";
export default function CohortLiveSessionCard({ lesson }) {
  return <Placeholder title={lesson.title || "Live Session"} type="cohort_live_session" phase="C" />;
}
