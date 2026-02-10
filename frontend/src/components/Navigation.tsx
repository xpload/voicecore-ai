import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Box,
  IconButton,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Phone as PhoneIcon,
  Analytics as AnalyticsIcon,
  People as PeopleIcon,
  Settings as SettingsIcon,
  Menu as MenuIcon,
} from '@mui/icons-material';
import { useAppStore } from '@/store';
import ThemeToggle from './ThemeToggle';

const drawerWidth = 240;

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Call Center', icon: <PhoneIcon />, path: '/calls' },
  { text: 'Analytics', icon: <AnalyticsIcon />, path: '/analytics' },
  { text: 'CRM', icon: <PeopleIcon />, path: '/crm' },
  { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
];

const Navigation: React.FC = () => {
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { sidebarOpen, toggleSidebar } = useAppStore();

  const drawer = (
    <>
      <Toolbar sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <IconButton onClick={toggleSidebar} edge="start">
            <MenuIcon />
          </IconButton>
          {sidebarOpen && (
            <Typography variant="h6" noWrap component="div" sx={{ ml: 2 }}>
              VoiceCore AI
            </Typography>
          )}
        </Box>
        {sidebarOpen && <ThemeToggle />}
      </Toolbar>
      <Box sx={{ overflow: 'auto', flexGrow: 1 }}>
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                component={Link}
                to={item.path}
                selected={location.pathname === item.path}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: 'primary.main',
                    color: 'primary.contrastText',
                    '&:hover': {
                      backgroundColor: 'primary.dark',
                    },
                    '& .MuiListItemIcon-root': {
                      color: 'primary.contrastText',
                    },
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                {sidebarOpen && <ListItemText primary={item.text} />}
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
    </>
  );

  return (
    <Drawer
      variant={isMobile ? 'temporary' : 'permanent'}
      open={isMobile ? sidebarOpen : true}
      onClose={isMobile ? toggleSidebar : undefined}
      sx={{
        width: sidebarOpen ? drawerWidth : 60,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: sidebarOpen ? drawerWidth : 60,
          boxSizing: 'border-box',
          transition: 'width 0.3s',
          overflowX: 'hidden',
        },
      }}
    >
      {drawer}
    </Drawer>
  );
};

export default Navigation;
