import type { Metadata } from "next";

import { PeopleCardsView } from "@/views/people-cards";

export const metadata: Metadata = {
  title: "People & Cards",
};

export default function PeoplePage() {
  return <PeopleCardsView />;
}
