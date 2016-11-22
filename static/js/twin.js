var app = angular.module('TWIN', []);

app.controller('TwinController', function($scope, $http, $timeout) {

    $scope.preference = null;
    $scope.somechange = false;

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
        $scope.selected = response.data;
    });

    $scope.select = function(student) {
        $scope.selected = student;
        $scope.somechange = true;
    }

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
                        $scope.selected = ui.item.student;
                        $scope.somechange = true;
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
                        $scope.somechange = true;
                        $scope.selected = null;
                    })
                }
            })
        }
    });

    $scope.save = function() {
        if($scope.selected !== $scope.preference) {
            $scope.saving = true;

            if($scope.selected === null) {
                var post = 'null';
            } else {
                var post = {student_number: $scope.selected.student_number};
            }
            $http.post('/api/preference', post).then(function(response) {
                $scope.saving = false;
                if(response.data == null) {
                    $scope.preference = null
                } else {
                    $scope.preference = $scope.selected;
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