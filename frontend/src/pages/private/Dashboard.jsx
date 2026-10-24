import { useState } from "react";
import { PageHeader, Segmented } from "../../components/ui/index.jsx";
import EncroachmentDashboard from "../../components/dashboard/EncroachmentDashboard.jsx";
import IntrusionDashboard from "../../components/dashboard/IntrusionDashboard.jsx";

const TABS = [
  ["encroachment", "Encroachment"],
  ["intrusion", "Intrusion"],
];

const DESCRIPTION = {
  encroachment: "Photographs, sites and reports of physical encroachment on railway land.",
  intrusion: "Confirmed intrusions into the track zone across every analysed video.",
};

export default function Dashboard() {
  const [tab, setTab] = useState("encroachment");
  return (
    <>
      <PageHeader
        crumbs={[["Dashboard"]]}
        title="Command dashboard"
        description={DESCRIPTION[tab]}
        actions={<Segmented options={TABS} value={tab} onChange={setTab} onCanvas label="Module" />}
      />
      {tab === "encroachment" ? <EncroachmentDashboard /> : <IntrusionDashboard />}
    </>
  );
}
