import type { ContactListItem } from "@/lib/api/types";

interface Props {
  contacts: ContactListItem[];
}

export function ContactTable({ contacts }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
          <tr>
            <th className="px-4 py-3">Contact</th>
            <th className="px-4 py-3">State</th>
            <th className="px-4 py-3">Attempts</th>
            <th className="px-4 py-3">Last outcome</th>
            <th className="px-4 py-3">Last attempt</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white text-sm">
          {contacts.map((contact) => (
            <tr key={contact.id}>
              <td className="px-4 py-3">
                <div className="font-medium text-slate-900">{contact.phone_number}</div>
                <div className="text-xs text-slate-500">{contact.email ?? "—"}</div>
              </td>
              <td className="px-4 py-3 capitalize">{contact.state.replace("_", " ")}</td>
              <td className="px-4 py-3">{contact.attempts_count}</td>
              <td className="px-4 py-3">{contact.last_outcome ?? "—"}</td>
              <td className="px-4 py-3">{contact.last_attempt_at ? new Date(contact.last_attempt_at).toLocaleString() : "—"}</td>
            </tr>
          ))}
          {contacts.length === 0 ? (
            <tr>
              <td colSpan={5} className="px-4 py-5 text-center text-slate-500">
                No contacts to display.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}