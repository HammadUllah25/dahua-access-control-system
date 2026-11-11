import { Led, type LedStatus } from "@/common/led"
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

type AttentionCard = {
  id: number
  personName: string
  department: string
  cardNumber: string
  controller: string
  status: LedStatus
  statusLabel: string
  validUntil: string
}

function CardsNeedingAttention({ cards }: { cards: AttentionCard[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cards needing attention</CardTitle>
        <CardDescription>
          Failed syncs, expiring validity and disabled cards across washrooms
        </CardDescription>
      </CardHeader>
      <div className="border-t border-border">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-4">Person</TableHead>
              <TableHead>Card</TableHead>
              <TableHead>Washroom</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="pr-4 text-right">Valid until</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {cards.map((card) => (
              <TableRow key={card.id}>
                <TableCell className="pl-4">
                  <p className="font-medium">{card.personName}</p>
                  <p className="text-xs text-muted-foreground">
                    {card.department}
                  </p>
                </TableCell>
                <TableCell className="font-mono">{card.cardNumber}</TableCell>
                <TableCell className="text-muted-foreground">
                  {card.controller}
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center gap-1.5 text-xs font-medium">
                    <Led status={card.status} />
                    {card.statusLabel}
                  </span>
                </TableCell>
                <TableCell className="pr-4 text-right font-mono text-muted-foreground">
                  {card.validUntil}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Card>
  )
}

export { CardsNeedingAttention, type AttentionCard }
