/**
 * Navigation Component
 *
 * Sidebar navigation for the dashboard with route links and status indicators.
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  HomeIcon,
  CpuChipIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';

interface NavItemProps {
  to: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  label: string;
}

const NavItem: React.FC<NavItemProps> = ({ to, icon: Icon, label }) => {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
          isActive
            ? 'bg-blue-600 text-white'
            : 'text-gray-400 hover:bg-gray-800 hover:text-white'
        }`
      }
    >
      <Icon className="w-5 h-5" />
      <span className="font-medium">{label}</span>
    </NavLink>
  );
};

const Navigation: React.FC = () => {
  return (
    <nav className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
      {/* Logo/Brand */}
      <div className="px-4 py-6 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <CpuChipIcon className="w-8 h-8 text-blue-500" />
          <div>
            <h2 className="text-lg font-bold text-white">Trading Bot</h2>
            <p className="text-xs text-gray-400">Workflow Dashboard</p>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <NavItem to="/" icon={HomeIcon} label="Dashboard" />
        <NavItem to="/workflows" icon={BoltIcon} label="Workflows" />
        <NavItem to="/bots" icon={CpuChipIcon} label="Bots" />
        <NavItem to="/metrics" icon={ChartBarIcon} label="Metrics" />
        <NavItem
          to="/emergency"
          icon={ExclamationTriangleIcon}
          label="Emergency"
        />
        <NavItem to="/history" icon={ClockIcon} label="History" />
        <NavItem to="/events" icon={BoltIcon} label="Live Events" />
      </div>

      {/* Footer Info */}
      <div className="px-4 py-4 border-t border-gray-700">
        <div className="text-xs text-gray-500">
          <p className="font-medium text-gray-400">System Status</p>
          <p className="mt-1">Infrastructure: Active</p>
          <p>WebSocket: Connected</p>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
