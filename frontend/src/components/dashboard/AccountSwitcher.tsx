/**
 * Account Switcher Component
 *
 * アカウント切り替えタブ
 */
import React from 'react';
import {
  Box,
  Tabs,
  Tab,
  Chip,
} from '@mui/material';
import { EbayAccount } from '../../types';
import AllInclusiveIcon from '@mui/icons-material/AllInclusive';
import PersonIcon from '@mui/icons-material/Person';

interface AccountSwitcherProps {
  accounts: EbayAccount[];
  selectedAccountId: string | null;
  onAccountChange: (accountId: string | null) => void;
}

const AccountSwitcher: React.FC<AccountSwitcherProps> = ({
  accounts,
  selectedAccountId,
  onAccountChange,
}) => {
  const handleChange = (_event: React.SyntheticEvent, newValue: string) => {
    // "all" の場合は null を渡す
    onAccountChange(newValue === 'all' ? null : newValue);
  };

  return (
    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
      <Tabs
        value={selectedAccountId || 'all'}
        onChange={handleChange}
        variant="scrollable"
        scrollButtons="auto"
        aria-label="account switcher tabs"
      >
        <Tab
          icon={<AllInclusiveIcon />}
          iconPosition="start"
          label="All Accounts"
          value="all"
          sx={{ textTransform: 'none' }}
        />
        {accounts.map((account) => (
          <Tab
            key={account.id}
            icon={<PersonIcon />}
            iconPosition="start"
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <span>{account.username || account.ebay_user_id}</span>
                {account.marketplace_id && (
                  <Chip
                    label={account.marketplace_id}
                    size="small"
                    variant="outlined"
                    sx={{ height: 20, fontSize: '0.7rem' }}
                  />
                )}
              </Box>
            }
            value={account.id}
            sx={{ textTransform: 'none' }}
          />
        ))}
      </Tabs>
    </Box>
  );
};

export default AccountSwitcher;
