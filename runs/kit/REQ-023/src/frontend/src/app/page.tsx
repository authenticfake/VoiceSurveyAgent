/**
 * Home page - redirects to campaigns.
 * REQ-023: Frontend campaign management UI
 */

import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/campaigns');
}