var app = angular.module('TWIN', []);

app.controller('TwinController', function($scope, $http, $timeout) {

    $scope.preference = null;

    // Get the list of all the students
    $http.get('/api/students').then(function(response) {
        $scope.students = response.data;
    });

    // Get the user information
    $http.get('/api/user').then(function(response) {
        $scope.user = response.data;
    });

    // Get the user preference information
    $http.get('/api/preference').then(function(response) {
        $scope.preference = response.data;
    });


    // Fill the autocomplete
    $scope.$watch('students', function(students) {
        if(students) {
            var source = students.map(function(student) {
                return {'value': student.name, 'student': student};
            });

            $( "#student" ).autocomplete({
                source: source,
                delay: 0,
                select: function(event, ui) {
                    // Call with timeout to make sure the whole $digest cycle keeps working
                    $timeout(function() {
                        $scope.changePreference(ui.item.student);
                    })
                }
            }).data("ui-autocomplete")._renderItem = function( ul, item ) {
                var li = $("<li>");
                if(item.student.reciprocal) {
                    li.addClass('reciprocal');
                }
                li.append( item.label )
                    .appendTo( ul );
                return li;
            }

            $('#student').on('input change', function(e) {
                if($(this).val() === '') {
                    $timeout(function() {
                        $scope.changePreference(null);
                    })
                }
            })
        }
    });


    $scope.changePreference = function(student) {
        if(student !== $scope.preference) {
            $scope.preference = student;

            if(student === null) {
                var post = 'null';
            } else {
                var post = {student_number: student.student_number};
            }
            $http.post('/api/preference', post).then(function(response) {
                if(response.data) {
                    angular.copy(response.data, $scope.preference);
                }
            });
        }
    }


    /* DEBUG!!! */
    $scope.$watch('debug_user', function(student) {
        if(student) {
            window.location.replace("/debug/quickswitch/" + student.student_number);
        }
    });
    /* END DEBUG!!! */

})