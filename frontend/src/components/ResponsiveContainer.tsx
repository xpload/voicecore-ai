import React from 'react';
import { Box, Container, useMediaQuery, useTheme } from '@mui/material';

interface ResponsiveContainerProps {
  children: React.ReactNode;
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | false;
  disableGutters?: boolean;
}

const ResponsiveContainer: React.FC<ResponsiveContainerProps> = ({
  children,
  maxWidth = 'xl',
  disableGutters = false,
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.down('md'));

  return (
    <Container
      maxWidth={maxWidth}
      disableGutters={disableGutters}
      sx={{
        px: isMobile ? 1 : isTablet ? 2 : 3,
        py: isMobile ? 2 : 3,
      }}
    >
      <Box
        sx={{
          width: '100%',
          minHeight: '100%',
        }}
      >
        {children}
      </Box>
    </Container>
  );
};

export default ResponsiveContainer;
