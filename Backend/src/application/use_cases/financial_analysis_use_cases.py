"""Use cases for financial analysis."""
from typing import List, Dict, Any, Optional
from datetime import datetime

from ...domain.entities.financial_record import FinancialRecord, Anomaly, BranchSummary
from ...domain.repositories.financial_repository import (
    FinancialRecordRepository,
    AnomalyRepository,
    BranchRepository,
    DataFileRepository
)
from ...domain.services.financial_service import FinancialAnalysisService, AnomalyAnalysisService


class LoadFinancialDataUseCase:
    """Use case for loading financial data from files."""
    
    def __init__(
        self,
        financial_repo: FinancialRecordRepository,
        data_file_repo: DataFileRepository,
        anomaly_repo: AnomalyRepository
    ):
        self.financial_repo = financial_repo
        self.data_file_repo = data_file_repo
        self.anomaly_repo = anomaly_repo
        self.analysis_service = FinancialAnalysisService()
    
    async def execute(self, file_path: Optional[str] = None) -> Dict[str, Any]:
        """Load financial data from file and perform initial analysis."""
        try:
            # Get file path
            if not file_path:
                file_path = await self.data_file_repo.get_default_file()
                if not file_path:
                    return {
                        'success': False,
                        'message': 'No default file available',
                        'data': {}
                    }
            
            # Validate file
            if not await self.data_file_repo.validate_file(file_path):
                return {
                    'success': False,
                    'message': f'Invalid file: {file_path}',
                    'data': {}
                }
            
            # Load records from file
            records = await self.data_file_repo.load_from_file(file_path)
            
            if not records:
                return {
                    'success': False,
                    'message': 'No records found in file',
                    'data': {}
                }
            
            # Save records to repository
            await self.financial_repo.save_many(records)
            
            # Detect anomalies
            anomalies = self.analysis_service.detect_anomalies(records)
            await self.anomaly_repo.save_many(anomalies)
            
            # Calculate metrics
            metrics = self.analysis_service.calculate_financial_metrics(records)
            branch_summaries = self.analysis_service.calculate_branch_summary(records)
            
            return {
                'success': True,
                'message': f'Successfully loaded {len(records)} records',
                'data': {
                    'records_count': len(records),
                    'json_data': [record.to_dict() for record in records],
                    'anomalies': [anomaly.to_dict() for anomaly in anomalies],
                    'metrics': metrics,
                    'branch_summaries': [bs.to_dict() for bs in branch_summaries],
                    'file_path': file_path
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error loading data: {str(e)}',
                'data': {}
            }


class GetFinancialSummaryUseCase:
    """Use case for getting financial summary."""
    
    def __init__(
        self,
        financial_repo: FinancialRecordRepository,
        anomaly_repo: AnomalyRepository
    ):
        self.financial_repo = financial_repo
        self.anomaly_repo = anomaly_repo
        self.analysis_service = FinancialAnalysisService()
        self.anomaly_service = AnomalyAnalysisService()
    
    async def execute(self) -> Dict[str, Any]:
        """Get comprehensive financial summary."""
        try:
            # Get all records
            records = await self.financial_repo.find_all()
            anomalies = await self.anomaly_repo.find_all()
            
            if not records:
                return {
                    'success': True,
                    'message': 'No financial data available',
                    'data': {
                        'records_count': 0,
                        'metrics': {},
                        'anomalies_summary': {},
                        'branch_summaries': []
                    }
                }
            
            # Calculate metrics
            metrics = self.analysis_service.calculate_financial_metrics(records)
            branch_summaries = self.analysis_service.calculate_branch_summary(records)
            anomaly_summary = self.anomaly_service.get_anomaly_summary(anomalies)
            
            return {
                'success': True,
                'message': f'Summary for {len(records)} records',
                'data': {
                    'records_count': len(records),
                    'metrics': metrics,
                    'anomalies_summary': anomaly_summary,
                    'branch_summaries': [bs.to_dict() for bs in branch_summaries]
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error generating summary: {str(e)}',
                'data': {}
            }


class GetBranchAnalysisUseCase:
    """Use case for branch-specific analysis."""
    
    def __init__(
        self,
        financial_repo: FinancialRecordRepository,
        branch_repo: BranchRepository
    ):
        self.financial_repo = financial_repo
        self.branch_repo = branch_repo
        self.analysis_service = FinancialAnalysisService()
    
    async def execute(self, branch_id: Optional[int] = None) -> Dict[str, Any]:
        """Get branch analysis."""
        try:
            if branch_id:
                # Get specific branch data
                records = await self.financial_repo.find_by_branch(branch_id)
                branch_summary = await self.branch_repo.find_by_id(branch_id)
                
                if not records:
                    return {
                        'success': False,
                        'message': f'No records found for branch {branch_id}',
                        'data': {}
                    }
                
                metrics = self.analysis_service.calculate_financial_metrics(records)
                
                return {
                    'success': True,
                    'message': f'Analysis for branch {branch_id}',
                    'data': {
                        'branch_id': branch_id,
                        'branch_summary': branch_summary.to_dict() if branch_summary else None,
                        'metrics': metrics,
                        'records_count': len(records),
                        'transactions': [record.to_dict() for record in records]
                    }
                }
            else:
                # Get all branches analysis
                all_records = await self.financial_repo.find_all()
                branch_summaries = self.analysis_service.calculate_branch_summary(all_records)
                
                return {
                    'success': True,
                    'message': f'Analysis for all {len(branch_summaries)} branches',
                    'data': {
                        'total_branches': len(branch_summaries),
                        'branch_summaries': [bs.to_dict() for bs in branch_summaries],
                        'top_performing': sorted(
                            branch_summaries, 
                            key=lambda x: x.saldo_neto, 
                            reverse=True
                        )[:5]
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error in branch analysis: {str(e)}',
                'data': {}
            }


class GetAnomalyAnalysisUseCase:
    """Use case for anomaly analysis."""
    
    def __init__(self, anomaly_repo: AnomalyRepository):
        self.anomaly_repo = anomaly_repo
        self.anomaly_service = AnomalyAnalysisService()
    
    async def execute(
        self, 
        severity_filter: Optional[str] = None,
        anomaly_type_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get anomaly analysis with optional filters."""
        try:
            # Get anomalies with filters
            if severity_filter:
                anomalies = await self.anomaly_repo.find_by_severity(severity_filter)
            elif anomaly_type_filter:
                anomalies = await self.anomaly_repo.find_by_type(anomaly_type_filter)
            else:
                anomalies = await self.anomaly_repo.find_all()
            
            # Analyze anomalies
            summary = self.anomaly_service.get_anomaly_summary(anomalies)
            categorized = self.anomaly_service.categorize_anomalies(anomalies)
            
            return {
                'success': True,
                'message': f'Found {len(anomalies)} anomalies',
                'data': {
                    'total_anomalies': len(anomalies),
                    'summary': summary,
                    'categorized': {
                        category: [anomaly.to_dict() for anomaly in category_anomalies]
                        for category, category_anomalies in categorized.items()
                    },
                    'anomalies': [anomaly.to_dict() for anomaly in anomalies]
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error in anomaly analysis: {str(e)}',
                'data': {}
            }


class QueryFinancialDataUseCase:
    """Use case for querying financial data."""
    
    def __init__(self, financial_repo: FinancialRecordRepository):
        self.financial_repo = financial_repo
        self.analysis_service = FinancialAnalysisService()
    
    async def execute(
        self,
        query_type: str,
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute financial data query based on type."""
        if parameters is None:
            parameters = {}
        
        try:
            if query_type == "all":
                records = await self.financial_repo.find_all()
                message = f"Retrieved all {len(records)} records"
                
            elif query_type == "by_branch":
                branch_id = parameters.get("branch_id")
                if not branch_id:
                    return {
                        'success': False,
                        'message': 'Branch ID is required',
                        'data': {}
                    }
                records = await self.financial_repo.find_by_branch(int(branch_id))
                message = f"Retrieved {len(records)} records for branch {branch_id}"
                
            elif query_type == "by_date_range":
                start_date = parameters.get("start_date")
                end_date = parameters.get("end_date")
                if not start_date or not end_date:
                    return {
                        'success': False,
                        'message': 'Start date and end date are required',
                        'data': {}
                    }
                records = await self.financial_repo.find_by_date_range(
                    datetime.fromisoformat(start_date),
                    datetime.fromisoformat(end_date)
                )
                message = f"Retrieved {len(records)} records for date range"
                
            elif query_type == "by_transaction_type":
                transaction_type = parameters.get("transaction_type")
                if not transaction_type:
                    return {
                        'success': False,
                        'message': 'Transaction type is required',
                        'data': {}
                    }
                records = await self.financial_repo.find_by_transaction_type(transaction_type)
                message = f"Retrieved {len(records)} {transaction_type} records"
                
            else:
                return {
                    'success': False,
                    'message': f'Unknown query type: {query_type}',
                    'data': {}
                }
            
            # Calculate metrics for the result set
            metrics = self.analysis_service.calculate_financial_metrics(records)
            
            return {
                'success': True,
                'message': message,
                'data': {
                    'records_count': len(records),
                    'records': [record.to_dict() for record in records],
                    'metrics': metrics,
                    'query_type': query_type,
                    'parameters': parameters
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error executing query: {str(e)}',
                'data': {}
            }