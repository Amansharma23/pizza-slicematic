"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { UserOrder } from "@/lib/api";
import { formatINR, roundFinalAmount } from "@/lib/utils";
import { Download, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";

interface BillModalProps {
  order: UserOrder | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function BillModal({ order, open, onOpenChange }: BillModalProps) {
  if (!order) return null;

  const handlePrint = () => {
    window.print();
  };

  const roundedTotal = roundFinalAmount(order.total);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md print:max-w-none print:w-full print:border-none print:shadow-none print:p-0 print:m-0">
        <DialogHeader className="print:hidden">
          <DialogTitle>Order Bill</DialogTitle>
        </DialogHeader>
        
        {/* Printable Area */}
        <div className="space-y-4 p-4 print:p-8 print:bg-white print:text-black">
          <div className="text-center space-y-1 border-b pb-4">
            <h2 className="text-2xl font-bold font-heading">SliceMatic</h2>
            <p className="text-sm text-muted-foreground print:text-black">Tax Invoice</p>
            <p className="text-sm">Order No: {order.order_no}</p>
            <p className="text-sm">Date: {new Date(order.created_at).toLocaleString()}</p>
          </div>

          <div className="space-y-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2">Item</th>
                  <th className="text-right py-2">Qty</th>
                  <th className="text-right py-2">Price</th>
                  <th className="text-right py-2">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {order.items?.map((item, idx) => (
                  <tr key={idx} className="group">
                    <td className="py-3 pr-2">
                      <div className="font-medium">{item.pizza}</div>
                      <div className="text-xs text-muted-foreground print:text-black">Base: {item.base}</div>
                      {item.toppings && item.toppings.length > 0 && (
                        <div className="text-xs text-muted-foreground print:text-black">
                          + {item.toppings.join(", ")}
                        </div>
                      )}
                    </td>
                    <td className="py-3 text-right align-top">{item.quantity}</td>
                    <td className="py-3 text-right align-top">{formatINR(item.unit_price)}</td>
                    <td className="py-3 text-right align-top font-medium">{formatINR(item.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="space-y-1.5 border-t pt-4 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground print:text-black">Subtotal</span>
                <span>{formatINR(order.subtotal)}</span>
              </div>
              {order.discount > 0 && (
                <div className="flex justify-between text-primary">
                  <span>Discount</span>
                  <span>-{formatINR(order.discount)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground print:text-black">GST (18%)</span>
                <span>{formatINR(order.gst)}</span>
              </div>
              <div className="flex justify-between font-bold text-lg pt-2 border-t">
                <span>Total (Rounded)</span>
                <span>{formatINR(roundedTotal)}</span>
              </div>
            </div>
            
            <div className="text-center pt-8 text-sm text-muted-foreground print:text-black">
              Thank you for dining with SliceMatic!
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t print:hidden">
          <Button onClick={handlePrint} className="gap-2">
            <Download className="size-4" /> Download PDF
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
