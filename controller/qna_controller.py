from flask import (
    jsonify,
    Blueprint,
    request,
    g
)
from flask_request_validator import (
    GET,
    PATH,
    JSON,
    validate_params,
    Param
)
from sqlalchemy import exc
from utils import login_required

def create_qna_endpoints(services, Session):
    qna_service = services
    qna_bp = Blueprint('qna', __name__, url_prefix = '/api/qna')

    @qna_bp.route('/', methods = ['GET'], endpoint = 'get_qna_list')
    @login_required(Session)
    @validate_params(
        Param('PRODUCT_NAME', GET, str, required = False),
        Param('PRDUCT_INQRY_NO', GET, int, required = False),
        Param('MD_KO_NAME', GET, str, required = False),
        Param('ORDER_NO', GET, int, required = False),
        Param('inquiryType', GET, str, required = False),
        Param('filterDateFrom', GET, str, required = False),
        Param('filterDateTo', GET, str, required = False),
        Param('filterLimit', GET, int, required = False),
        Param('page', GET, int, required = False)
    )
    def get_qna_list(*args, **kwargs):
        """
        Q&A list를 보여주는 함수
        valildate_params를 통과한 QueryString을 인자로 받는다.

        Args:
            PRODUCT_NAME : 상품명
            PRDUCT_INQRY_NO : 글 번호
            MD_KO_NAME : 셀러 한글명
            ORDER_NO : 회원번호
            inquiryType : 문의 유형
            filterDateFrom : 등록일 ~부터
            filterDateTo : 등록일 ~까지
            filterLimit : pagination offset
            page : page number
        Returns:
            qna_list : 조건을 충족하는 Q&A 목록 (r'type : dict)
            qna_count : 전체 갯수와 조건을 만족하는 Q&A 갯수 (r'type : dict)
            DB_CONNECTION_ERROR, 500
        Authors:
            hj885353@gmail.com (김해준)
        History:
            2020-10-05 (hj885353@gmail.com) : 초기 생성
            2020-10-12 (hj885353@gmail.com) : QueryString 변경
            2020-10-13 (hj885353@gmail.com) : pagination 관련 QueryString이 입력되지 않았을 경우를 위한 default값 설정
        """
        valid_param = {}

        valid_param['PRODUCT_NAME']    = args[0] # 상품명
        valid_param['PRDUCT_INQRY_NO'] = args[1] # 글 번호
        valid_param['MD_KO_NAME']      = args[2] # 셀러 한글명
        valid_param['ORDER_NO']        = args[3] # 회원 번호
        valid_param['inquiryType']     = args[4] # 문의 유형
        valid_param['filterDateFrom']  = args[5] # 등록일 ~부터
        valid_param['filterDateTo']    = args[6] # 등록일 ~까지
        valid_param['filterLimit']     = args[7] if args[7] else 20 # pagination limit
        valid_param['page']            = args[8] if args[8] else 1 # page number

        # decorator로부터 받아온 seller info를 가진 g 객체
        seller_info = g.seller_info

        try:
            # db connection
            session = Session()
            if session:
                # dao와 service를 거친 결과 목록 반환
                qna_list_result = qna_service.get_qna_list(valid_param, seller_info, session)
                # tuple -> list로 casting
                qna_list, qna_count, page_number = qna_list_result
                return jsonify({'qna' : qna_list, 'total_qna_number' : qna_count, 'page_number' : page_number})
            else:
                # db connection error
                return jsonify({'message': 'NO_DATABASE_CONNECTION'}), 500

        except Exception as e:
            return jsonify({'message': f'{e}'}), 500

        finally:
            # db close
            session.close()

    @qna_bp.route('/<int:parameter_question_no>', methods = ['GET'], endpoint = 'qna_answer_info')
    @login_required(Session)
    @validate_params(
        Param('parameter_question_no', PATH, int, required = True)
    )
    def qna_answer_info(*args, **kwargs):
        """
        Q&A list에서 답변하기 버튼 눌렀을 때, 해당 문의에 대한 info를 return해주는 API

        Args:
            valid_param : validate_params에서 통과 한 QueryString. 글 번호를 받아서 해당 글 번호에 대한 info를 return
            session : db connection 객체
        Returns:
            qna_answer_result : 해당 글 번호에 해당하는 글 번호, 문의 유형, 닉네임, 상품명, 상품 이미지, 문의 내용, 문의 생성 시간을 return (r'type : dict)
        Authors:
            hj885353@gmail.com (김해준)
        History:
            2020-10-06 (hj885353@gmail.com) : 초기 생성
            2020-10-06 (hj885353@gmail.com) : QueryString을 path_parameter로 수정
        """
        # validate_params를 통과 한 QueryString을 dictionary 형태로 변수에 할당
        valid_param = {
            'parameter_question_no' : args[0]
        }

        session = Session()

        try:
            if session:
                # service로부터 받은 result를 response
                qna_answer_result = qna_service.qna_answer_info(valid_param, session)

                return jsonify({'qna_answer' : qna_answer_result})
            else:
                # db connection error
                return jsonify({'message': 'NO_DATABASE_CONNECTION'}), 500

        except Exception as e:
            return jsonify({'message': f'{e}'}), 500

        finally:
            session.close()

    @qna_bp.route('/<int:parameter_question_no>', methods = ['POST'], endpoint = 'insert_answer')
    @login_required(Session)
    @validate_params(
        Param('parameter_question_no', PATH, int, required = True),
        Param('answer', JSON, str, required = True)
    )
    def insert_answer(*args, **kwargs):
        """
        문의 사항에 대해서 답변을 저장하는 API
        
        path_parameter와 답변 내용, 로그인 된 셀러에 대한 정보를 받아 service의 함수로 전달해준다.

        Args:
            valid_param : 글 번호를 가리키는 PATH PARAMETER, 답변 내용인 answer, 답변 단 사람을 표시하기 위해 login한 seller_id를 가져옴
            session : db connection 객체
        Returns:
            SUCCESS, 200
            DB_ERROR, 500
        Authors:
            hj885353@gmail.com (김해준)
        History:
            2020-10-06 (hj885353@gmail.com) : 초기 생성
        """
        # path_parameter로 글 번호와 답변 내용을 받고, 로그인 데코레이터로부터 로그인 된 셀러에 대한 정보를 받음
        valid_param = {
            'parameter_question_no': args[0],
            'answer'               : args[1],
            'seller_info'          : g.seller_info
        }
        
        session = Session()

        try:
            if session:
                # service로 인자 전달
                qna_service.insert_answer(valid_param, session)
                # 정상 동작 시 commit
                session.commit()

                return jsonify({'message' : 'SUCCESS'})
            else:
                # db connection error
                return jsonify({'message': 'NO_DATABASE_CONNECTION'}), 500

        except Exception as e:
            # 에러 발생 시 롤백
            session.rollback()
            return jsonify({'message': f'{e}'}), 500

        finally:
            session.close()

    @qna_bp.route('/<int:parameter_question_no>', methods = ['PUT'], endpoint = 'delete_answer')
    @login_required(Session)
    @validate_params(
        Param('parameter_question_no', PATH, int, required = True)
    )
    def delete_question(*args, **kwargs):
        """
        문의 사항에 대해서 답변을 삭제하는 API
        
        PUT method를 사용하여 is_deleted의 상태를 변경한다.
        validate_params를 통과한 값을 인자로 받고 해당 인자를 service의 함수로 전달해준다.

        Args:
            valid_param : 글 번호를 가리키는 PATH PARAMETER
            session : db connection 객체
        Returns:
            SUCCESS, 200
            DB_ERROR, 500
        Authors:
            hj885353@gmail.com (김해준)
        History:
            2020-10-06 (hj885353@gmail.com) : 초기 생성
        """
        valid_param = {
            'parameter_question_no': args[0],
        }
    
        # db connection 객체 생성    
        session = Session()

        try:
            if session:
                # service로 인자 전달
                qna_service.delete_question(valid_param, session)
                # 정상 동작 시 commit
                session.commit()

                return jsonify({'message' : 'SUCCESS'})
            else:
                # db connection error
                return jsonify({'message': 'NO_DATABASE_CONNECTION'}), 500

        except Exception as e:
            # 에러 발생 시 롤백
            session.rollback()
            return jsonify({'message': f'{e}'}), 500

        finally:
            session.close()

    return qna_bp