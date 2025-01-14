# -*- coding: utf-8 -*-
from copy import deepcopy
from odoo import models, api, _, fields

class AccountChartOfAccountReport(models.AbstractModel):
    _name = "account.trial.net.movement.report"
    _description = "Trial Balance with Net Movement Report"
    _inherit = "account.report"

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_comparison = {'date_from': '', 'date_to': '', 'filter': 'no_comparison', 'number_period': 1}
    filter_all_entries = False
    filter_journals = True
    filter_analytic = True
    filter_unfold_all = False
    filter_cash_basis = None
    filter_hierarchy = False
    MAX_LINES = None

    @api.model
    def _get_templates(self):
        templates = super(AccountChartOfAccountReport, self)._get_templates()
        templates['main_template'] = 'account_reports.main_template_with_filter_input_accounts'
        return templates

    @api.model
    def _get_columns(self, options):
        header1 = [
            {'name': '', 'style': 'width:40%'},
            {'name': _('Initial Balance'), 'class': 'number', 'colspan': 2},
        ] + [
            {'name': period['string'], 'class': 'number', 'colspan': 2}
            for period in reversed(options['comparison'].get('periods', []))
        ] + [
            {'name': options['date']['string'], 'class': 'number', 'colspan': 2},
            {'name': _('Trial Balance - End'), 'class': 'number', 'colspan': 2},
        ] + [
            {'name': _(''), 'class': 'number'},
        ]
        header2 = [
            {'name': '', 'style': 'width:40%'},
            {'name': _('Debit'), 'class': 'number o_account_coa_column_contrast'},
            {'name': _('Credit'), 'class': 'number o_account_coa_column_contrast'},
        ]
        if options.get('comparison') and options['comparison'].get('periods'):
            header2 += [
                {'name': _('Debit'), 'class': 'number o_account_coa_column_contrast'},
                {'name': _('Credit'), 'class': 'number o_account_coa_column_contrast'},
            ] * len(options['comparison']['periods'])
        header2 += [
            {'name': _('Debit'), 'class': 'number o_account_coa_column_contrast'},
            {'name': _('Credit'), 'class': 'number o_account_coa_column_contrast'},
            {'name': _('Debit'), 'class': 'number o_account_coa_column_contrast'},
            {'name': _('Credit'), 'class': 'number o_account_coa_column_contrast'},
            {'name': _('Net Movement'), 'class': 'number o_account_coa_column_contrast'},
        ]
        return [header1, header2]

    @api.model
    def _get_lines(self, options, line_id=None):
        # Create new options with 'unfold_all' to compute the initial balances.
        # Then, the '_do_query' will compute all sums/unaffected earnings/initial balances for all comparisons.
        new_options = options.copy()
        new_options['unfold_all'] = True
        options_list = self._get_options_periods_list(new_options)
        accounts_results, taxes_results = self.env['account.general.ledger']._do_query(options_list, fetch_lines=False)
        names = []
        lines = []
        totals = [0.0] * (2 * (len(options_list) + 2) + 1)

        # Add lines, one per account.account record.
        for account, periods_results in accounts_results:
            sums = []
            account_balance = 0.0
            for i, period_values in enumerate(reversed(periods_results)):
                account_sum = period_values.get('sum', {})
                account_un_earn = period_values.get('unaffected_earnings', {})
                account_init_bal = period_values.get('initial_balance', {})

                if i == 0:
                    # Append the initial balances.
                    initial_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
                    sums += [
                        initial_balance > 0 and initial_balance or 0.0,
                        initial_balance < 0 and -initial_balance or 0.0,
                    ]
                    account_balance += initial_balance

                # Append the debit/credit columns.
                sums += [
                    account_sum.get('debit', 0.0) - account_init_bal.get('debit', 0.0),
                    account_sum.get('credit', 0.0) - account_init_bal.get('credit', 0.0),
                ]
                sums += [
                    sums[2] + sums[0],
                    sums[3] + sums[1],
                ]
                account_balance += sums[-4] - sums[-3]

            # Append the totals.
            sums += [
                account_balance or 0.0
            ]

            # account.account report line.
            columns = []
            for i, value in enumerate(sums):
                # Update totals.
                totals[i] += value

                # Create columns.
                columns.append({'name': self.format_value(value, blank_if_zero=True), 'class': 'number', 'no_format_name': value})

            name = account.name_get()[0][1]
            if name not in names:
                lines.append({
                    'id': account.id,
                    'name': name,
                    'title_hover': name,
                    'columns': columns,
                    'unfoldable': False,
                    'caret_options': 'account.account',
                    'class': 'o_account_searchable_line o_account_coa_column_contrast',
                })
                names.append(name)
            else:
                get_line = self.build_dict(lines, key="name")
                get_index = get_line.get(name)
                for i in range(len(columns)):
                    lines[get_index['index']]['columns'][i]['no_format_name'] += columns[i]['no_format_name']
                    lines[get_index['index']]['columns'][i]['name'] = self.format_value(lines[get_index['index']]['columns'][i]['no_format_name'], blank_if_zero=True)

        #Initialize original data and data for manipulation
        get_lines = self.build_dict(lines, key="name")
        test_lines = self.build_dict(lines, key="name")
        for line in get_lines:
            #Remove lines with zero netmovement
            if get_lines[line]['columns'][6]['no_format_name'] == 0:
                test_lines
                # del test_lines[line]
        lines = []

        #return the dict to list
        for line in test_lines:
            lines.append(test_lines[line])

        # Total report line.
        lines.append({
             'id': 'grouped_accounts_total',
             'name': _('Total'),
             'class': 'total o_account_coa_column_contrast',
             'columns': [{'name': self.format_value(total), 'class': 'number'} for total in totals],
             'level': 1,
        })
        return lines

    @api.model
    def _get_report_name(self):
        return _("Trial Balance with Net Movement")

    def build_dict(self,seq, key):
        return dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))
