jest.mock('axios', () => ({ get: jest.fn(), post: jest.fn() }));
import { render, screen, fireEvent } from '@testing-library/react';
import Confirmation from './components/Confirmation';
import Navbar from './components/Navbar';
test('shows student branding', () => {
  render(<Navbar />);
  expect(screen.getByText(/Stevens student edition/i)).toBeInTheDocument();
});
test('requires date review before importing, even after connecting', () => {
  sessionStorage.setItem('snapshot_session','test');
  render(<Confirmation events={[{title:'CS Lab',type:'lab',days:['Monday']}]} setEvents={jest.fn()} onConfirmComplete={jest.fn()} />);
  expect(screen.getByRole('button',{name:/Add 1 Events/})).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button',{name:/Add 1 Events/}));
  expect(screen.getByRole('alert')).toHaveTextContent(/Set semester dates/);
  sessionStorage.clear();
});
