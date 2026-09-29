'''Default parameters for reconciliation engine.'''

from decimal import Decimal

DATE_TOLERANCE_DAYS = 2
FUZZY_THRESHOLD = 85
VALUE_TOLERANCE = Decimal('0.00')
MAX_FILE_SIZE_MB = 20
MAX_ROWS_WARNING = 20000
SUPPORTED_EXTENSIONS = ('.csv', '.xls', '.xlsx')
PT_REQUIRED_COLUMNS = ('Data', 'Descrição', 'Valor')
APP_VERSION = '1.0.0'
