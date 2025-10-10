import React from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Container, Box, Typography } from '@mui/material';
import { theme } from './theme/theme';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="lg">
        <Box
          sx={{
            marginTop: 8,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Typography component="h1" variant="h3" gutterBottom>
            eBay Trend Research Tool
          </Typography>
          <Typography variant="h6" color="text.secondary" align="center">
            出品商品のパフォーマンスをモニタリングし、トレンド商品を発見
          </Typography>
          <Box sx={{ mt: 4 }}>
            <Typography variant="body1" color="text.secondary">
              開発中... Phase 1 完了
            </Typography>
          </Box>
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;
